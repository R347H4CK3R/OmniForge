// Export bounded pseudocode from an authorized binary using Ghidra Headless.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.program.model.listing.Function;
import ghidra.util.task.ConsoleTaskMonitor;
import java.io.File;
import java.io.PrintWriter;

public class OmniForgeDecompile extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) throw new IllegalArgumentException("output filename required");
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        decompiler.setSimplificationStyle("decompile");
        int examined = 0, successful = 0;
        try (PrintWriter out = new PrintWriter(new File(args[0]), "UTF-8")) {
            out.println("/* Decompiled pseudocode. NOT original application source. */");
            for (Function function : currentProgram.getFunctionManager().getFunctions(true)) {
                if (monitor.isCancelled() || examined >= 500) break;
                examined++;
                if (function.isExternal()) continue;
                var result = decompiler.decompileFunction(function, 12, new ConsoleTaskMonitor());
                if (!result.decompileCompleted() || result.getDecompiledFunction() == null) continue;
                String code = result.getDecompiledFunction().getC();
                if (code.length() > 40000) code = code.substring(0, 40000) + "\n/* truncated */";
                out.println("\n/* " + function.getName() + " @ " + function.getEntryPoint() + " */");
                out.println(code);
                successful++;
            }
            out.println("\n/* Decompiled " + successful + " of " + examined + " enumerated functions. */");
        } finally { decompiler.dispose(); }
    }
}
