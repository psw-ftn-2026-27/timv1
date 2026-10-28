using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace TeamTracker.Analyzers;

internal sealed class ProjectTypes
{
    private readonly Compilation _compilation;
    private readonly string _root;
    private readonly ConcurrentDictionary<IAssemblySymbol, bool> _assemblies;

    public ProjectTypes(Compilation compilation, string root)
    {
        _compilation = compilation;
        _root = root;
        _assemblies = new ConcurrentDictionary<IAssemblySymbol, bool>(SymbolEqualityComparer.Default);
    }

    public bool Contains(ITypeSymbol type)
    {
        if (type is not INamedTypeSymbol named)
        {
            return false;
        }

        if (named.IsAnonymousType)
        {
            return false;
        }

        var definition = named.OriginalDefinition;
        if (definition.Locations.Any(l => l.IsInSource))
        {
            return true;
        }

        var assembly = definition.ContainingAssembly;
        return assembly is not null && _assemblies.GetOrAdd(assembly, IsRepositoryAssembly);
    }

    public int Coupling(TypeDeclarationSyntax declaration, SemanticModel model, INamedTypeSymbol self)
    {
        var found = new HashSet<INamedTypeSymbol>(SymbolEqualityComparer.Default);
        foreach (var node in declaration.DescendantNodes())
        {
            if (node is TypeSyntax type && type is not PredefinedTypeSyntax)
            {
                Collect(model.GetSymbolInfo(type).Symbol as ITypeSymbol, found);
            }
            if (node is ExpressionSyntax expression)
            {
                Collect(model.GetTypeInfo(expression).Type, found);
            }
        }

        var own = self.OriginalDefinition;
        return found.Count(t => t.TypeKind == TypeKind.Class && !SymbolEqualityComparer.Default.Equals(t, own) && Contains(t));
    }

    private static void Collect(ITypeSymbol? type, ISet<INamedTypeSymbol> found)
    {
        switch (type)
        {
            case IArrayTypeSymbol array:
                Collect(array.ElementType, found);
                break;
            case IPointerTypeSymbol pointer:
                Collect(pointer.PointedAtType, found);
                break;
            case INamedTypeSymbol named:
                found.Add(named.OriginalDefinition);
                foreach (var argument in named.TypeArguments)
                {
                    Collect(argument, found);
                }
                break;
        }
    }

    private bool IsRepositoryAssembly(IAssemblySymbol assembly)
    {
        if (_root.Length == 0)
        {
            return false;
        }

        if (_compilation.GetMetadataReference(assembly) is not PortableExecutableReference reference)
        {
            return false;
        }

        var path = Scope.Normalize(reference.FilePath);
        return path.StartsWith(_root + "/", StringComparison.OrdinalIgnoreCase)
               && path.IndexOf("/.nuget/", StringComparison.OrdinalIgnoreCase) < 0;
    }
}
