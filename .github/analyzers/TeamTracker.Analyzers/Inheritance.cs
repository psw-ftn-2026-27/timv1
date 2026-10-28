using System.Collections.Concurrent;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Diagnostics;

namespace TeamTracker.Analyzers;

internal sealed class Inheritance
{
    private readonly bool _measure;
    private readonly ConcurrentDictionary<INamedTypeSymbol, TypeDeclarationSyntax> _classes;
    private readonly ConcurrentDictionary<INamedTypeSymbol, byte> _bases;

    public Inheritance(bool measure)
    {
        _measure = measure;
        _classes = new ConcurrentDictionary<INamedTypeSymbol, TypeDeclarationSyntax>(SymbolEqualityComparer.Default);
        _bases = new ConcurrentDictionary<INamedTypeSymbol, byte>(SymbolEqualityComparer.Default);
    }

    public void Add(INamedTypeSymbol symbol, TypeDeclarationSyntax declaration)
    {
        _classes.TryAdd(symbol.OriginalDefinition, declaration);
        if (symbol.BaseType is { } baseType)
        {
            _bases.TryAdd(baseType.OriginalDefinition, 0);
        }
    }

    public void Report(CompilationAnalysisContext context, ProjectTypes projectTypes)
    {
        foreach (var pair in _classes)
        {
            var declaration = pair.Value;
            var name = declaration.Identifier.ValueText;
            var location = declaration.Identifier.GetLocation();
            var depth = Depth(pair.Key, projectTypes);
            var hasSubclass = _bases.ContainsKey(pair.Key);

            if (!hasSubclass)
            {
                Reporter.Report(context.ReportDiagnostic, context.Options, Rules.Dit, depth,
                    new Measured(name, "class", location, declaration));
            }

            if (_measure)
            {
                Reporter.Measure(context.ReportDiagnostic, new Measured(name, "inheritance", location, declaration),
                    ("dit", depth), ("hasSubclass", hasSubclass ? 1 : 0));
            }
        }
    }

    private static int Depth(INamedTypeSymbol type, ProjectTypes projectTypes)
    {
        var depth = 0;
        var current = type.BaseType;
        while (current is not null && current.SpecialType != SpecialType.System_Object && projectTypes.Contains(current))
        {
            depth++;
            current = current.BaseType;
        }
        return depth;
    }
}
