import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

import com.github.javaparser.JavaParser;
import com.github.javaparser.ParseResult;
import com.github.javaparser.ParserConfiguration;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.ImportDeclaration;
import com.github.javaparser.ast.body.ClassOrInterfaceDeclaration;
import com.github.javaparser.ast.body.ConstructorDeclaration;
import com.github.javaparser.ast.body.FieldDeclaration;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.body.Parameter;
import com.github.javaparser.ast.expr.AssignExpr;
import com.github.javaparser.ast.expr.MethodCallExpr;
import com.github.javaparser.ast.expr.MethodReferenceExpr;
import com.github.javaparser.ast.expr.ObjectCreationExpr;
import com.github.javaparser.ast.body.VariableDeclarator;
import com.github.javaparser.ast.stmt.ExplicitConstructorInvocationStmt;
import com.github.javaparser.ast.visitor.VoidVisitorAdapter;

public class JavaParserRunner {
    private static class Result {
        String language = "java";
        String filePath;
        String moduleQualifiedName;
        List<String> defs = new ArrayList<>();
        List<String> callEdges = new ArrayList<>();
        List<String> importEdges = new ArrayList<>();
        List<String> assignmentHints = new ArrayList<>();
        boolean parseOk = true;
        String error = null;
    }

    private static class ContextVisitor extends VoidVisitorAdapter<Void> {
        private static class Scope {
            final String name;
            final String kind;

            Scope(String name, String kind) {
                this.name = name;
                this.kind = kind;
            }
        }

        private final String moduleQname;
        private final Result result;
        private final Deque<Scope> scope = new ArrayDeque<>();

        ContextVisitor(String moduleQname, Result result) {
            this.moduleQname = moduleQname;
            this.result = result;
            this.scope.push(new Scope(moduleQname, "module"));
        }

        private String currentScope() {
            return scope.peek().name;
        }

        private String currentScopeKind() {
            return scope.peek().kind;
        }

        private String normalizeType(String rawType) {
            if (rawType == null) {
                return "";
            }
            String value = rawType.trim();
            if (value.isEmpty()) {
                return "";
            }
            int genericPos = value.indexOf('<');
            if (genericPos > 0) {
                value = value.substring(0, genericPos).trim();
            }
            if (value.endsWith("[]")) {
                value = value.substring(0, value.length() - 2).trim();
            }
            return value;
        }

        @Override
        public void visit(ClassOrInterfaceDeclaration node, Void arg) {
            String scopeKind = currentScopeKind();
            if ("method".equals(scopeKind)) {
                // Nested classes inside callables are implementation detail.
                super.visit(node, arg);
                return;
            }
            String parent = "class".equals(scopeKind) ? currentScope() : moduleQname;
            String qname = parent + "." + node.getNameAsString();
            int start = node.getRange().map(r -> r.begin.line).orElse(1);
            int end = node.getRange().map(r -> r.end.line).orElse(start);
            String enclosing = "class".equals(scopeKind) ? currentScope() : "";
            result.defs.add(
                String.format(
                    "%s|class|%d|%d|%s|%s|",
                    qname,
                    start,
                    end,
                    node.getNameAsString(),
                    enclosing
                )
            );
            scope.push(new Scope(qname, "class"));
            super.visit(node, arg);
            scope.pop();
        }

        @Override
        public void visit(MethodDeclaration node, Void arg) {
            String classScope = currentScope();
            String qname = classScope + "." + node.getNameAsString();
            int start = node.getRange().map(r -> r.begin.line).orElse(1);
            int end = node.getRange().map(r -> r.end.line).orElse(start);
            result.defs.add(
                String.format(
                    "%s|method|%d|%d|%s||%s",
                    qname,
                    start,
                    end,
                    node.getNameAsString(),
                    classScope
                )
            );
            scope.push(new Scope(qname, "method"));
            super.visit(node, arg);
            scope.pop();
        }

        @Override
        public void visit(ConstructorDeclaration node, Void arg) {
            String classScope = currentScope();
            String qname = classScope + "." + node.getNameAsString();
            int start = node.getRange().map(r -> r.begin.line).orElse(1);
            int end = node.getRange().map(r -> r.end.line).orElse(start);
            result.defs.add(
                String.format(
                    "%s|method|%d|%d|%s||%s",
                    qname,
                    start,
                    end,
                    node.getNameAsString(),
                    classScope
                )
            );
            scope.push(new Scope(qname, "method"));
            super.visit(node, arg);
            scope.pop();
        }

        @Override
        public void visit(FieldDeclaration node, Void arg) {
            if ("class".equals(currentScopeKind())) {
                String typeName = normalizeType(node.getElementType().asString());
                if (!typeName.isEmpty()) {
                    String constructorScope = currentScope() + ".constructor";
                    for (VariableDeclarator variable : node.getVariables()) {
                        String receiver = "this." + variable.getNameAsString().trim();
                        result.assignmentHints.add(
                            String.format("%s|%s|%s", constructorScope, receiver, typeName)
                        );
                    }
                }
            }
            super.visit(node, arg);
        }

        @Override
        public void visit(Parameter node, Void arg) {
            String scopeKind = currentScopeKind();
            if ("method".equals(scopeKind)) {
                String typeName = normalizeType(node.getType().asString());
                String receiver = node.getNameAsString().trim();
                if (!receiver.isEmpty() && !typeName.isEmpty()) {
                    result.assignmentHints.add(
                        String.format("%s|%s|%s", currentScope(), receiver, typeName)
                    );
                }
            }
            super.visit(node, arg);
        }

        @Override
        public void visit(VariableDeclarator node, Void arg) {
            if ("method".equals(currentScopeKind())) {
                String receiver = node.getNameAsString().trim();
                String valueText = normalizeType(node.getType().asString());
                if (!receiver.isEmpty() && !valueText.isEmpty()) {
                    result.assignmentHints.add(
                        String.format("%s|%s|%s", currentScope(), receiver, valueText)
                    );
                }
            }
            super.visit(node, arg);
        }

        @Override
        public void visit(MethodCallExpr node, Void arg) {
            String callee = node.getNameAsString();
            String calleeQname = "";
            if (node.getScope().isPresent()) {
                String scopeText = node.getScope().get().toString();
                if (scopeText != null && !scopeText.isBlank()) {
                    calleeQname = scopeText + "." + callee;
                }
            }
            boolean dynamic = false;
            if (callee.equals("forName") && node.getScope().isPresent()) {
                if (node.getScope().get().toString().equals("Class")) {
                    dynamic = true;
                }
            }
            String caller = currentScope();
            result.callEdges.add(String.format("%s|%s|%s|%s", caller, callee, calleeQname, dynamic));
            super.visit(node, arg);
        }

        @Override
        public void visit(ObjectCreationExpr node, Void arg) {
            String callee = node.getType().getNameAsString();
            String calleeQname = node.getType().toString();
            String caller = currentScope();
            result.callEdges.add(String.format("%s|%s|%s|%s", caller, callee, calleeQname, false));
            super.visit(node, arg);
        }

        @Override
        public void visit(MethodReferenceExpr node, Void arg) {
            String callee = node.getIdentifier();
            String calleeQname = "";
            if (node.getScope() != null) {
                String scopeText = node.getScope().toString();
                if (scopeText != null && !scopeText.isBlank()) {
                    calleeQname = scopeText + "." + callee;
                }
            }
            String caller = currentScope();
            result.callEdges.add(String.format("%s|%s|%s|%s", caller, callee, calleeQname, false));
            super.visit(node, arg);
        }

        @Override
        public void visit(ExplicitConstructorInvocationStmt node, Void arg) {
            String callee = node.isThis() ? "this" : "super";
            String calleeQname = callee;
            String caller = currentScope();
            result.callEdges.add(String.format("%s|%s|%s|%s", caller, callee, calleeQname, false));
            super.visit(node, arg);
        }

        @Override
        public void visit(AssignExpr node, Void arg) {
            String scopeKind = currentScopeKind();
            if ("method".equals(scopeKind)) {
                String targetText = node.getTarget().toString().trim();
                String receiver = targetText;
                if (receiver.contains(".")) {
                    receiver = receiver.substring(receiver.lastIndexOf('.') + 1).trim();
                }
                String valueText = node.getValue().toString().trim();
                if (!receiver.isEmpty() && !valueText.isEmpty()) {
                    result.assignmentHints.add(
                        String.format("%s|%s|%s", currentScope(), receiver, valueText)
                    );
                }
            }
            super.visit(node, arg);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("Usage: JavaParserRunner <list_file>");
            System.exit(2);
        }
        List<Result> results = new ArrayList<>();
        List<String> lines = Files.readAllLines(new File(args[0]).toPath(), StandardCharsets.UTF_8);
        ParserConfiguration config = new ParserConfiguration();
        JavaParser parser = new JavaParser(config);

        for (String line : lines) {
            if (line.trim().isEmpty()) {
                continue;
            }
            String[] parts = line.split("\t", 2);
            if (parts.length != 2) {
                continue;
            }
            String filePath = parts[0];
            String moduleQname = parts[1];
            Result result = new Result();
            result.filePath = filePath;
            result.moduleQualifiedName = moduleQname;
            try {
                String source = Files.readString(new File(filePath).toPath(), StandardCharsets.UTF_8);
                ParseResult<CompilationUnit> parsed = parser.parse(source);
                if (!parsed.getResult().isPresent()) {
                    result.parseOk = false;
                    result.error = "Parse error";
                    results.add(result);
                    continue;
                }
                CompilationUnit unit = parsed.getResult().get();
                for (ImportDeclaration imp : unit.getImports()) {
                    result.importEdges.add(String.format("%s|%s|%s", moduleQname, imp.getNameAsString(), false));
                }
                ContextVisitor visitor = new ContextVisitor(moduleQname, result);
                visitor.visit(unit, null);
            } catch (Exception exc) {
                result.parseOk = false;
                result.error = exc.getMessage();
            }
            results.add(result);
        }

        StringBuilder out = new StringBuilder();
        out.append("{\"results\":[");
        for (int i = 0; i < results.size(); i++) {
            Result r = results.get(i);
            if (i > 0) {
                out.append(",");
            }
            out.append("{");
            out.append("\"language\":\"").append(r.language).append("\",");
            out.append("\"file_path\":\"").append(escape(r.filePath)).append("\",");
            out.append("\"module_qualified_name\":\"").append(escape(r.moduleQualifiedName)).append("\",");
            out.append("\"defs\":[");
            for (int j = 0; j < r.defs.size(); j++) {
                if (j > 0) out.append(",");
                out.append("\"").append(escape(r.defs.get(j))).append("\"");
            }
            out.append("],");
            out.append("\"call_edges\":[");
            for (int j = 0; j < r.callEdges.size(); j++) {
                if (j > 0) out.append(",");
                out.append("\"").append(escape(r.callEdges.get(j))).append("\"");
            }
            out.append("],");
            out.append("\"import_edges\":[");
            for (int j = 0; j < r.importEdges.size(); j++) {
                if (j > 0) out.append(",");
                out.append("\"").append(escape(r.importEdges.get(j))).append("\"");
            }
            out.append("],");
            out.append("\"assignment_hints\":[");
            for (int j = 0; j < r.assignmentHints.size(); j++) {
                if (j > 0) out.append(",");
                out.append("\"").append(escape(r.assignmentHints.get(j))).append("\"");
            }
            out.append("],");
            out.append("\"parse_ok\":").append(r.parseOk ? "true" : "false");
            out.append(",\"error\":");
            if (r.error == null) {
                out.append("null");
            } else {
                out.append("\"").append(escape(r.error)).append("\"");
            }
            out.append("}");
        }
        out.append("]}");
        System.out.print(out.toString());
    }

    private static String escape(String value) {
        if (value == null) return "";
        return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n");
    }
}
