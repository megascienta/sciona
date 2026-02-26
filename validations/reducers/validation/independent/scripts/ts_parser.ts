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

function expressionText(expr) {
  if (!expr) return null;
  if (ts.isIdentifier(expr)) return expr.text;
  if (ts.isNewExpression(expr)) return expressionText(expr.expression);
  if (ts.isPropertyAccessExpression(expr)) {
    const left = expressionText(expr.expression);
    if (left) return `${left}.${expr.name.text}`;
    return expr.name.text;
  }
  return null;
}

function memberName(node, sourceFile) {
  if (!node) return null;
  if (ts.isIdentifier(node)) return node.text;
  if (ts.isPrivateIdentifier(node)) return node.text;
  if (ts.isStringLiteral(node) || ts.isNumericLiteral(node)) return node.text;
  if (ts.isComputedPropertyName(node)) {
    const computed = expressionText(node.expression);
    if (computed) return computed;
    const text = node.getText(sourceFile).trim();
    if (text.startsWith("[") && text.endsWith("]") && text.length > 2) {
      return text.slice(1, -1).trim();
    }
  }
  return null;
}

function decoratorsOf(node) {
  if (!node) return [];
  if (typeof ts.canHaveDecorators === "function" && ts.canHaveDecorators(node)) {
    const decorators = ts.getDecorators(node);
    return decorators || [];
  }
  return [];
}

function typeHintText(node, sourceFile) {
  if (!node) return null;
  if (ts.isTypeReferenceNode(node)) {
    if (ts.isIdentifier(node.typeName)) return node.typeName.text;
    return node.typeName.getText(sourceFile);
  }
  const raw = node.getText(sourceFile).trim();
  if (!raw) return null;
  const genericPos = raw.indexOf("<");
  if (genericPos > 0) return raw.slice(0, genericPos).trim();
  return raw;
}

function parseFile(entry) {
  const content = fs.readFileSync(entry.path, "utf8");
  const sourceFile = ts.createSourceFile(entry.path, content, ts.ScriptTarget.Latest, true);

  const defs = [];
  const call_edges = [];
  const import_edges = [];
  const assignment_hints = [];

  const scopeStack = [{ name: entry.module_qualified_name, kind: "module" }];

  function currentScope() {
    return scopeStack[scopeStack.length - 1].name;
  }

  function currentScopeKind() {
    return scopeStack[scopeStack.length - 1].kind;
  }

  function pushScope(name, kind) {
    scopeStack.push({ name, kind });
  }

  function popScope() {
    scopeStack.pop();
  }

  function registerCallable(kind, qname, node, visitNode) {
    const span = lineSpan(sourceFile, node);
    defs.push({ kind, qualified_name: qname, start_line: span.start_line, end_line: span.end_line });
    const decorators = decoratorsOf(node);
    for (const decorator of decorators) {
      const expr = decorator.expression;
      const callee = ts.isCallExpression(expr) ? calleeName(expr.expression) : calleeName(expr);
      const qnameHint = ts.isCallExpression(expr) ? expressionText(expr.expression) : expressionText(expr);
      const text = expr ? expr.getText(sourceFile) : "decorator";
      call_edges.push({
        caller: qname,
        callee: callee || "",
        callee_qname: qnameHint || "",
        dynamic: true,
        callee_text: `decorator:${text}`
      });
    }
    pushScope(qname, kind);
    visitNode();
    popScope();
  }

  function visit(node) {
    if (
      ts.isVariableDeclaration(node) &&
      (currentScopeKind() === "function" || currentScopeKind() === "method") &&
      ts.isIdentifier(node.name) &&
      node.initializer
    ) {
      const valueText = expressionText(node.initializer);
      if (valueText) {
        assignment_hints.push({
          scope: currentScope(),
          receiver: node.name.text,
          value_text: valueText
        });
      }
    }
    if (
      ts.isParameter(node) &&
      currentScopeKind() === "method" &&
      currentScope().endsWith(".constructor") &&
      ts.isIdentifier(node.name)
    ) {
      const modifiers = node.modifiers || [];
      const hasFieldModifier = modifiers.some(mod =>
        mod.kind === ts.SyntaxKind.PublicKeyword ||
        mod.kind === ts.SyntaxKind.PrivateKeyword ||
        mod.kind === ts.SyntaxKind.ProtectedKeyword ||
        mod.kind === ts.SyntaxKind.ReadonlyKeyword
      );
      if (hasFieldModifier && node.type) {
        const valueText = typeHintText(node.type, sourceFile);
        if (valueText) {
          assignment_hints.push({
            scope: currentScope(),
            receiver: `this.${node.name.text}`,
            value_text: valueText
          });
        }
      }
    }
    if (
      ts.isBinaryExpression(node) &&
      node.operatorToken &&
      node.operatorToken.kind === ts.SyntaxKind.EqualsToken &&
      (currentScopeKind() === "function" || currentScopeKind() === "method")
    ) {
      const lhs = expressionText(node.left);
      const valueText = expressionText(node.right);
      if (lhs && valueText) {
        assignment_hints.push({
          scope: currentScope(),
          receiver: lhs,
          value_text: valueText
        });
      }
    }
    if (ts.isImportDeclaration(node)) {
      const moduleName = node.moduleSpecifier.text;
      const bindings = [];
      const clause = node.importClause;
      if (clause) {
        if (clause.name) {
          bindings.push(`default:${clause.name.text}`);
        }
        if (clause.namedBindings) {
          if (ts.isNamespaceImport(clause.namedBindings)) {
            bindings.push(`namespace:${clause.namedBindings.name.text}`);
          } else if (ts.isNamedImports(clause.namedBindings)) {
            for (const element of clause.namedBindings.elements) {
              const imported = element.propertyName ? element.propertyName.text : element.name.text;
              const local = element.name.text;
              bindings.push(`named:${imported}->${local}`);
            }
          }
        }
      }
      import_edges.push({
        source_module: entry.module_qualified_name,
        target_module: moduleName,
        dynamic: false,
        target_text: bindings.length ? bindings.join(",") : null
      });
    }
    if (ts.isExportDeclaration(node) && node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) {
      import_edges.push({
        source_module: entry.module_qualified_name,
        target_module: node.moduleSpecifier.text,
        dynamic: false,
        target_text: null
      });
    }
    if (ts.isImportEqualsDeclaration(node)) {
      const moduleReference = node.moduleReference;
      if (ts.isExternalModuleReference(moduleReference) && moduleReference.expression && ts.isStringLiteral(moduleReference.expression)) {
        import_edges.push({
          source_module: entry.module_qualified_name,
          target_module: moduleReference.expression.text,
          dynamic: false
        });
      }
    }

    if (ts.isCallExpression(node)) {
      let dynamic = false;
      if (node.expression && node.expression.kind === ts.SyntaxKind.ImportKeyword) {
        if (node.arguments.length !== 1 || !isStringLiteral(node.arguments[0])) {
          dynamic = true;
        } else {
          import_edges.push({
            source_module: entry.module_qualified_name,
            target_module: node.arguments[0].text,
            dynamic: false
          });
        }
      }
      if (ts.isIdentifier(node.expression) && node.expression.text === "require") {
        if (node.arguments.length !== 1 || !isStringLiteral(node.arguments[0])) {
          dynamic = true;
        } else {
          import_edges.push({ source_module: entry.module_qualified_name, target_module: node.arguments[0].text, dynamic: false });
        }
      }

      if (currentScopeKind() === "function" || currentScopeKind() === "method") {
        const callee = calleeName(node.expression);
        const calleeText = node.expression ? node.expression.getText(sourceFile) : "";
        const qnameHint = expressionText(node.expression);
        call_edges.push({
          caller: currentScope(),
          callee: callee || "",
          callee_qname: qnameHint || "",
          dynamic: dynamic || !callee,
          callee_text: calleeText || null
        });
      }
    }

    if (ts.isFunctionDeclaration(node) && node.name) {
      if (currentScopeKind() === "module") {
        const qname = `${entry.module_qualified_name}.${node.name.text}`;
        registerCallable("function", qname, node, () => ts.forEachChild(node, visit));
        return;
      }
      // Nested callables are implementation detail; keep caller attribution on parent.
      ts.forEachChild(node, visit);
      return;
    }

    if (
      ts.isVariableDeclaration(node) &&
      currentScopeKind() === "module" &&
      ts.isIdentifier(node.name) &&
      node.initializer &&
      (ts.isArrowFunction(node.initializer) || ts.isFunctionExpression(node.initializer))
    ) {
      const qname = `${entry.module_qualified_name}.${node.name.text}`;
      registerCallable("function", qname, node.initializer, () => ts.forEachChild(node.initializer, visit));
      return;
    }

    if (ts.isNewExpression(node)) {
      if (currentScopeKind() === "function" || currentScopeKind() === "method") {
        const callee = calleeName(node.expression);
        const calleeText = node.expression ? node.expression.getText(sourceFile) : "";
        const qnameHint = expressionText(node.expression);
        call_edges.push({
          caller: currentScope(),
          callee: callee || "",
          callee_qname: qnameHint || "",
          dynamic: !callee,
          callee_text: calleeText || null
        });
      }
    }

    if (ts.isClassDeclaration(node) && node.name) {
      const scopeKind = currentScopeKind();
      if (scopeKind === "function" || scopeKind === "method") {
        // Nested classes inside callables are implementation detail.
        ts.forEachChild(node, visit);
        return;
      }
      const parent = scopeKind === "class" ? currentScope() : entry.module_qualified_name;
      const qname = `${parent}.${node.name.text}`;
      registerCallable("class", qname, node, () => ts.forEachChild(node, visit));
      return;
    }

    if (ts.isClassExpression(node) && node.name) {
      const scopeKind = currentScopeKind();
      if (scopeKind === "function" || scopeKind === "method") {
        ts.forEachChild(node, visit);
        return;
      }
      const parent = scopeKind === "class" ? currentScope() : entry.module_qualified_name;
      const qname = `${parent}.${node.name.text}`;
      registerCallable("class", qname, node, () => ts.forEachChild(node, visit));
      return;
    }

    if (
      ts.isPropertyDeclaration(node) &&
      currentScopeKind() === "class" &&
      node.name &&
      node.initializer &&
      (ts.isArrowFunction(node.initializer) || ts.isFunctionExpression(node.initializer))
    ) {
      const classScope = currentScope();
      const name = memberName(node.name, sourceFile);
      if (!name) {
        ts.forEachChild(node, visit);
        return;
      }
      const qname = `${classScope}.${name}`;
      registerCallable("method", qname, node.initializer, () => ts.forEachChild(node.initializer, visit));
      return;
    }

    if (ts.isConstructorDeclaration(node) && currentScopeKind() === "class") {
      const classScope = currentScope();
      const qname = `${classScope}.constructor`;
      registerCallable("method", qname, node, () => ts.forEachChild(node, visit));
      return;
    }

    if (ts.isMethodDeclaration(node) && currentScopeKind() === "class" && node.name) {
      const classScope = currentScope();
      const name = memberName(node.name, sourceFile);
      if (!name) {
        ts.forEachChild(node, visit);
        return;
      }
      const qname = `${classScope}.${name}`;
      registerCallable("method", qname, node, () => ts.forEachChild(node, visit));
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
      assignment_hints,
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
      assignment_hints: [],
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
