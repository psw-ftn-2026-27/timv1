using System;
using System.Collections.Immutable;
using System.Globalization;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.Diagnostics;

namespace TeamTracker.Analyzers;

internal sealed class Measured
{
    public Measured(string name, string kind, Location location, SyntaxNode node)
    {
        Name = name;
        Kind = kind;
        Location = location;
        var span = node.GetLocation().GetLineSpan();
        StartLine = span.StartLinePosition.Line + 1;
        EndLine = span.EndLinePosition.Line + 1;
    }

    public string Name { get; }
    public string Kind { get; }
    public Location Location { get; }
    public int StartLine { get; }
    public int EndLine { get; }
}

internal static class Reporter
{
    public static void Report(Action<Diagnostic> report, AnalyzerOptions options, MetricRule rule,
        int value, Measured member)
    {
        var tree = member.Location.SourceTree;
        var config = tree is null
            ? options.AnalyzerConfigOptionsProvider.GlobalOptions
            : options.AnalyzerConfigOptionsProvider.GetOptions(tree);
        var suspect = Read(config, "tt_" + rule.Key + "_suspect", rule.DefaultSuspect);
        var critical = Read(config, "tt_" + rule.Key + "_critical", rule.DefaultCritical);

        var descriptor = value > critical ? rule.Critical : value > suspect ? rule.Suspect : null;
        if (descriptor is null)
        {
            return;
        }

        var isCritical = ReferenceEquals(descriptor, rule.Critical);
        var properties = ImmutableDictionary<string, string?>.Empty
            .Add("metric", rule.Label)
            .Add("value", Text(value))
            .Add("level", isCritical ? "critical" : "suspect")
            .Add("suspect", Text(suspect))
            .Add("critical", Text(critical))
            .Add("member", member.Name)
            .Add("kind", member.Kind)
            .Add("startLine", Text(member.StartLine))
            .Add("endLine", Text(member.EndLine));

        report(Diagnostic.Create(descriptor, member.Location, properties,
            rule.Label, value, member.Name, isCritical ? "kritično" : "sumnjivo", suspect, critical));
    }

    public static void Measure(Action<Diagnostic> report, Measured member, params (string Key, int Value)[] values)
    {
        var properties = ImmutableDictionary<string, string?>.Empty
            .Add("member", member.Name)
            .Add("kind", member.Kind)
            .Add("startLine", Text(member.StartLine))
            .Add("endLine", Text(member.EndLine));
        foreach (var (key, value) in values)
        {
            properties = properties.Add(key, Text(value));
        }

        report(Diagnostic.Create(Rules.Measure, member.Location, properties, member.Kind, member.Name));
    }

    private static int Read(AnalyzerConfigOptions config, string key, int fallback)
    {
        return config.TryGetValue(key, out var raw)
               && int.TryParse(raw.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var value)
            ? value
            : fallback;
    }

    private static string Text(int value)
    {
        return value.ToString(CultureInfo.InvariantCulture);
    }
}
