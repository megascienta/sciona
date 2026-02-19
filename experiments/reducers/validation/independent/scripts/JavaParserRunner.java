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
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.expr.MethodCallExpr;
import com.github.javaparser.ast.expr.ObjectCreationExpr;
import com.github.javaparser.ast.visitor.VoidVisitorAdapter;

public class JavaParserRunner {
    private static class Result {
        String language = "java";
        String filePath;
        String moduleQualifiedName;
        List<String> defs = new ArrayList<>();
        List<String> callEdges = new ArrayList<>();
        List<String> importEdges = new ArrayList<>();
        boolean parseOk = true;
        String error = null;
    }

    private static class ContextVisitor extends VoidVisitorAdapter<Void> {
        private final String moduleQname;
        private final Result result;
        private final Deque<String> scope = new ArrayDeque<>();

        ContextVisitor(String moduleQname, Result result) {
            this.moduleQname = moduleQname;
            this.result = result;
            this.scope.push(moduleQname);
        }

        private String currentScope() {
            return scope.peek();
        }

        @Override
        public void visit(ClassOrInterfaceDeclaration node, Void arg) {
            String qname = moduleQname + "." + node.getNameAsString();
            int start = node.getRange().map(r -> r.begin.line).orElse(1);
            int end = node.getRange().map(r -> r.end.line).orElse(start);
            result.defs.add(String.format("%s|class|%d|%d", qname, start, end));
            scope.push(qname);
            super.visit(node, arg);
            scope.pop();
        }

        @Override
        public void visit(MethodDeclaration node, Void arg) {
            String classScope = currentScope();
            String qname = classScope + "." + node.getNameAsString();
            int start = node.getRange().map(r -> r.begin.line).orElse(1);
            int end = node.getRange().map(r -> r.end.line).orElse(start);
            result.defs.add(String.format("%s|method|%d|%d", qname, start, end));
            scope.push(qname);
            super.visit(node, arg);
            scope.pop();
        }

        @Override
        public void visit(MethodCallExpr node, Void arg) {
            String callee = node.getNameAsString();
            boolean dynamic = false;
            if (callee.equals("forName") && node.getScope().isPresent()) {
                if (node.getScope().get().toString().equals("Class")) {
                    dynamic = true;
                }
            }
            String caller = currentScope();
            String calleeQname = moduleQname + "." + callee;
            result.callEdges.add(String.format("%s|%s|%s|%s", caller, callee, calleeQname, dynamic));
            super.visit(node, arg);
        }

        @Override
        public void visit(ObjectCreationExpr node, Void arg) {
            String callee = node.getType().getNameAsString();
            String caller = currentScope();
            String calleeQname = moduleQname + "." + callee;
            result.callEdges.add(String.format("%s|%s|%s|%s", caller, callee, calleeQname, false));
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
            } catch (IOException exc) {
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
