using System;
using System.Collections.Immutable;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Diagnostics;

namespace TeamTracker.Analyzers;

[DiagnosticAnalyzer(LanguageNames.CSharp)]
public sealed class MaintainabilityAnalyzer : DiagnosticAnalyzer
{
    private static readonly SyntaxKind[] MethodKinds =
    {
        SyntaxKind.MethodDeclaration,
        SyntaxKind.ConstructorDeclaration,
        SyntaxKind.DestructorDeclaration,
        SyntaxKind.OperatorDeclaration,
        SyntaxKind.ConversionOperatorDeclaration
    };

    public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics => Rules.Descriptors;

    public override void Initialize(AnalysisContext context)
    {
        context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);
        context.EnableConcurrentExecution();
        context.RegisterCompilationStartAction(OnCompilationStart);
    }

    private static void OnCompilationStart(CompilationStartAnalysisContext start)
    {
        if (Scope.IsTestAssembly(start.Compilation.AssemblyName))
        {
            return;
        }

        var global = start.Options.AnalyzerConfigOptionsProvider.GlobalOptions;
        global.TryGetValue("build_property.TtRepoRoot", out var root);
        global.TryGetValue("build_property.TtMeasure", out var measureFlag);
        var measure = string.Equals(measureFlag?.Trim(), "true", StringComparison.OrdinalIgnoreCase);
        var repositoryRoot = Scope.Normalize(root);
        var projectTypes = new ProjectTypes(start.Compilation, repositoryRoot);
        var inheritance = new Inheritance(measure);

        start.RegisterSyntaxNodeAction(c => AnalyzeMethod(c, repositoryRoot, measure), MethodKinds);
        start.RegisterSyntaxNodeAction(c => AnalyzeClass(c, repositoryRoot, measure, projectTypes, inheritance),
            SyntaxKind.ClassDeclaration, SyntaxKind.RecordDeclaration);
        start.RegisterCompilationEndAction(c => inheritance.Report(c, projectTypes));
    }

    private static void AnalyzeMethod(SyntaxNodeAnalysisContext context, string root, bool measure)
    {
        var method = (BaseMethodDeclarationSyntax)context.Node;
        if (!Scope.IsMeasured(method.SyntaxTree, root))
        {
            return;
        }

        var body = Metrics.BodyOf(method);
        if (body is null)
        {
            return;
        }

        var member = new Measured(Metrics.MemberName(method), "method", Metrics.MemberLocation(method), method);
        var meloc = Metrics.Meloc(method);
        var cyclo = Metrics.Cyclo(body);
        var nop = method.ParameterList.Parameters.Count;

        Reporter.Report(context.ReportDiagnostic, context.Options, Rules.Meloc, meloc, member);
        Reporter.Report(context.ReportDiagnostic, context.Options, Rules.Cyclo, cyclo, member);
        Reporter.Report(context.ReportDiagnostic, context.Options, Rules.Nop, nop, member);

        if (measure)
        {
            Reporter.Measure(context.ReportDiagnostic, member, ("meloc", meloc), ("cyclo", cyclo), ("nop", nop));
        }
    }

    private static void AnalyzeClass(SyntaxNodeAnalysisContext context, string root, bool measure,
        ProjectTypes projectTypes, Inheritance inheritance)
    {
        var declaration = (TypeDeclarationSyntax)context.Node;
        if (!Scope.IsMeasured(declaration.SyntaxTree, root))
        {
            return;
        }

        var member = new Measured(declaration.Identifier.ValueText, "class",
            declaration.Identifier.GetLocation(), declaration);
        var cloc = Metrics.CodeLines(declaration);
        var wmc = Metrics.Wmc(declaration);
        var nad = Metrics.Nad(declaration);
        var nmd = Metrics.Nmd(declaration);

        Reporter.Report(context.ReportDiagnostic, context.Options, Rules.Cloc, cloc, member);
        Reporter.Report(context.ReportDiagnostic, context.Options, Rules.Wmc, wmc, member);
        Reporter.Report(context.ReportDiagnostic, context.Options, Rules.Nad, nad, member);
        Reporter.Report(context.ReportDiagnostic, context.Options, Rules.Nmd, nmd, member);

        var cbo = 0;
        if (context.SemanticModel.GetDeclaredSymbol(declaration) is { } symbol)
        {
            cbo = projectTypes.Coupling(declaration, context.SemanticModel, symbol);
            Reporter.Report(context.ReportDiagnostic, context.Options, Rules.Cbo, cbo, member);
            inheritance.Add(symbol, declaration);
        }

        if (measure)
        {
            Reporter.Measure(context.ReportDiagnostic, member,
                ("cloc", cloc), ("wmc", wmc), ("nad", nad), ("nmd", nmd), ("cbo", cbo));
        }
    }
}
