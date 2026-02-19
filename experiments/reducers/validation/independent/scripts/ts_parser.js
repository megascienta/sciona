#!/usr/bin/env node

const fs = require("fs");
const ts = require("typescript");

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", chunk => data += chunk);
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

function lineSpan(sourceFile, node) {
  const start = sourceFile.getLineAndCharacterOfPosition(node.getStart());
  const end = sourceFile.getLineAndCharacterOfPosition(node.getEnd());
  return { start_line: start.line + 1, end_line: end.line + 1 };
}

function isStringLiteral(node) {
  return node && node.kind === ts.SyntaxKind.StringLiteral;
}

function calleeName(expr) {
  if (!expr) return null;
  if (ts.isIdentifier(expr)) return expr.text;
  if (ts.isPropertyAccessExpression(expr)) return expr.name.text;
  return null;
}

function parseFile(entry) {
  const content = fs.readFileSync(entry.path, "utf8");
  const sourceFile = ts.createSourceFile(entry.path, content, ts.ScriptTarget.Latest, true);

  const defs = [];
  const call_edges = [];
  const import_edges = [];

  const scopeStack = [entry.module_qualified_name];

  function currentScope() {
    return scopeStack[scopeStack.length - 1];
  }

  function visit(node) {
    if (ts.isImportDeclaration(node)) {
      const moduleName = node.moduleSpecifier.text;
      import_edges.push({ source_module: entry.module_qualified_name, target_module: moduleName, dynamic: false });
    }

    if (ts.isCallExpression(node)) {
      let dynamic = false;
      if (node.expression && node.expression.kind === ts.SyntaxKind.ImportKeyword) {
        if (node.arguments.length !== 1 || !isStringLiteral(node.arguments[0])) {
          dynamic = true;
        }
      }
      if (ts.isIdentifier(node.expression) && node.expression.text === "require") {
        if (node.arguments.length !== 1 || !isStringLiteral(node.arguments[0])) {
          dynamic = true;
        } else {
          import_edges.push({ source_module: entry.module_qualified_name, target_module: node.arguments[0].text, dynamic: false });
        }
      }

      const callee = calleeName(node.expression);
      if (callee) {
        call_edges.push({
          caller: currentScope(),
          callee: callee,
          callee_qname: `${entry.module_qualified_name}.${callee}`,
          dynamic: dynamic
        });
      }
    }

    if (ts.isFunctionDeclaration(node) && node.name) {
      const qname = `${entry.module_qualified_name}.${node.name.text}`;
      const span = lineSpan(sourceFile, node);
      defs.push({ kind: "function", qualified_name: qname, start_line: span.start_line, end_line: span.end_line });
      scopeStack.push(qname);
      ts.forEachChild(node, visit);
      scopeStack.pop();
      return;
    }

    if (ts.isClassDeclaration(node) && node.name) {
      const qname = `${entry.module_qualified_name}.${node.name.text}`;
      const span = lineSpan(sourceFile, node);
      defs.push({ kind: "class", qualified_name: qname, start_line: span.start_line, end_line: span.end_line });
      scopeStack.push(qname);
      ts.forEachChild(node, visit);
      scopeStack.pop();
      return;
    }

    if (ts.isMethodDeclaration(node) && node.name && ts.isIdentifier(node.name)) {
      const classScope = currentScope();
      const qname = `${classScope}.${node.name.text}`;
      const span = lineSpan(sourceFile, node);
      defs.push({ kind: "method", qualified_name: qname, start_line: span.start_line, end_line: span.end_line });
      scopeStack.push(qname);
      ts.forEachChild(node, visit);
      scopeStack.pop();
      return;
    }

    ts.forEachChild(node, visit);
  }

  try {
    ts.forEachChild(sourceFile, visit);
    return {
      language: "typescript",
      file_path: entry.file_path,
      module_qualified_name: entry.module_qualified_name,
      defs,
      call_edges,
      import_edges,
      parse_ok: true,
      error: null
    };
  } catch (err) {
    return {
      language: "typescript",
      file_path: entry.file_path,
      module_qualified_name: entry.module_qualified_name,
      defs: [],
      call_edges: [],
      import_edges: [],
      parse_ok: false,
      error: String(err)
    };
  }
}

async function main() {
  const raw = await readStdin();
  const input = JSON.parse(raw);
  const results = [];
  for (const entry of input.files) {
    results.push(parseFile(entry));
  }
  process.stdout.write(JSON.stringify({ results }));
}

main().catch(err => {
  process.stderr.write(String(err));
  process.exit(1);
});
