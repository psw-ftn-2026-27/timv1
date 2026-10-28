using System.Collections.Generic;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace TeamTracker.Analyzers;

internal static class Metrics
{
    public static int CodeLines(SyntaxNode node)
    {
        var lines = new HashSet<int>();
        foreach (var token in node.DescendantTokens())
        {
            var span = token.GetLocation().GetLineSpan();
            for (var i = span.StartLinePosition.Line; i <= span.EndLinePosition.Line; i++)
            {
                lines.Add(i);
            }
        }
        return lines.Count;
    }

    public static SyntaxNode? BodyOf(BaseMethodDeclarationSyntax method)
    {
        return (SyntaxNode?)method.Body ?? method.ExpressionBody?.Expression;
    }

    public static int Meloc(BaseMethodDeclarationSyntax method)
    {
        return method.ExpressionBody is not null ? CodeLines(method.ExpressionBody.Expression) : BodyLines(method.Body!);
    }

    private static int BodyLines(BlockSyntax body)
    {
        var lines = new HashSet<int>();
        foreach (var token in body.DescendantTokens())
        {
            if (token == body.OpenBraceToken || token == body.CloseBraceToken)
            {
                continue;
            }
            var span = token.GetLocation().GetLineSpan();
            for (var i = span.StartLinePosition.Line; i <= span.EndLinePosition.Line; i++)
            {
                lines.Add(i);
            }
        }
        return lines.Count;
    }

    public static int Cyclo(SyntaxNode body)
    {
        var count = 1;
        foreach (var node in body.DescendantNodesAndSelf())
        {
            switch (node)
            {
                case IfStatementSyntax:
                case WhileStatementSyntax:
                case ForStatementSyntax:
                case ForEachStatementSyntax:
                case ForEachVariableStatementSyntax:
                case SwitchStatementSyntax:
                case SwitchExpressionSyntax:
                case ContinueStatementSyntax:
                case GotoStatementSyntax:
                case ConditionalExpressionSyntax:
                case CatchClauseSyntax:
                    count++;
                    break;
                case BinaryExpressionSyntax binary when binary.IsKind(SyntaxKind.LogicalAndExpression)
                                                      || binary.IsKind(SyntaxKind.LogicalOrExpression)
                                                      || binary.IsKind(SyntaxKind.CoalesceExpression):
                    count++;
                    break;
                case BinaryPatternSyntax pattern when pattern.IsKind(SyntaxKind.AndPattern)
                                                    || pattern.IsKind(SyntaxKind.OrPattern):
                    count++;
                    break;
                case AssignmentExpressionSyntax assignment when assignment.IsKind(SyntaxKind.CoalesceAssignmentExpression):
                    count++;
                    break;
            }
        }
        return count;
    }

    public static int Wmc(TypeDeclarationSyntax declaration)
    {
        return declaration.Members.OfType<BaseMethodDeclarationSyntax>()
            .Sum(m => BodyOf(m) is SyntaxNode body ? Cyclo(body) : 0);
    }

    public static int Nad(TypeDeclarationSyntax declaration)
    {
        var fields = declaration.Members.OfType<FieldDeclarationSyntax>().Sum(f => f.Declaration.Variables.Count);
        var autoProperties = declaration.Members.OfType<PropertyDeclarationSyntax>().Count(IsAutoProperty);
        var recordParameters = declaration is RecordDeclarationSyntax record
            ? record.ParameterList?.Parameters.Count ?? 0
            : 0;
        return fields + autoProperties + recordParameters;
    }

    public static int Nmd(TypeDeclarationSyntax declaration)
    {
        return declaration.Members.OfType<MethodDeclarationSyntax>().Count();
    }

    public static string MemberName(BaseMethodDeclarationSyntax method)
    {
        return method switch
        {
            MethodDeclarationSyntax m => m.Identifier.ValueText,
            ConstructorDeclarationSyntax c => c.Identifier.ValueText + " (ctor)",
            DestructorDeclarationSyntax d => "~" + d.Identifier.ValueText,
            OperatorDeclarationSyntax o => "operator " + o.OperatorToken.ValueText,
            ConversionOperatorDeclarationSyntax c => "operator " + c.Type,
            _ => method.Kind().ToString()
        };
    }

    public static Location MemberLocation(BaseMethodDeclarationSyntax method)
    {
        return method switch
        {
            MethodDeclarationSyntax m => m.Identifier.GetLocation(),
            ConstructorDeclarationSyntax c => c.Identifier.GetLocation(),
            DestructorDeclarationSyntax d => d.Identifier.GetLocation(),
            OperatorDeclarationSyntax o => o.OperatorToken.GetLocation(),
            ConversionOperatorDeclarationSyntax c => c.Type.GetLocation(),
            _ => method.GetLocation()
        };
    }

    private static bool IsAutoProperty(PropertyDeclarationSyntax property)
    {
        return property.ExpressionBody is null
               && !property.Modifiers.Any(SyntaxKind.AbstractKeyword)
               && property.AccessorList is not null
               && property.AccessorList.Accessors.All(a => a.Body is null && a.ExpressionBody is null);
    }
}
