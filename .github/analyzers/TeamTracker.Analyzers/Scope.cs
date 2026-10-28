using System;
using System.Linq;
using Microsoft.CodeAnalysis;

namespace TeamTracker.Analyzers;

internal static class Scope
{
    public static bool IsTestAssembly(string? assemblyName)
    {
        return assemblyName is not null && IsTestName(assemblyName);
    }

    public static string Normalize(string? path)
    {
        return (path ?? string.Empty).Replace('\\', '/').TrimEnd('/');
    }

    public static bool IsMeasured(SyntaxTree tree, string root)
    {
        var path = Normalize(tree.FilePath);
        if (path.Length == 0)
        {
            return true;
        }

        if (root.Length > 0 && path.StartsWith(root + "/", StringComparison.OrdinalIgnoreCase))
        {
            path = path.Substring(root.Length + 1);
        }

        var parts = path.Split('/');
        var name = parts[parts.Length - 1];
        var directories = parts.Take(parts.Length - 1);

        if (directories.Any(d => d is "bin" or "obj" or "Migrations" || IsTestName(d)))
        {
            return false;
        }

        return !name.EndsWith(".Designer.cs", StringComparison.OrdinalIgnoreCase)
               && !name.EndsWith(".g.cs", StringComparison.OrdinalIgnoreCase)
               && !name.EndsWith(".g.i.cs", StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsTestName(string name)
    {
        return name.Equals("test", StringComparison.OrdinalIgnoreCase)
               || name.Equals("tests", StringComparison.OrdinalIgnoreCase)
               || name.EndsWith(".Test", StringComparison.OrdinalIgnoreCase)
               || name.EndsWith(".Tests", StringComparison.OrdinalIgnoreCase);
    }
}
