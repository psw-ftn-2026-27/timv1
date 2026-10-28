using System.Collections.Immutable;
using System.Linq;
using Microsoft.CodeAnalysis;

namespace TeamTracker.Analyzers;

internal sealed class MetricRule
{
    private const string Category = "Maintainability";
    private const string MessageFormat = "{0} = {1} u '{2}': {3} (sumnjivo > {4}, kritično > {5})";

    public MetricRule(string key, string suspectId, string criticalId, int defaultSuspect, int defaultCritical,
        string title, string description, bool compilationEnd)
    {
        Key = key;
        Label = key.ToUpperInvariant();
        DefaultSuspect = defaultSuspect;
        DefaultCritical = defaultCritical;
        var tags = compilationEnd ? new[] { WellKnownDiagnosticTags.CompilationEnd } : new string[0];
        Suspect = Create(suspectId, title, description, tags);
        Critical = Create(criticalId, title, description, tags);
    }

    public string Key { get; }
    public string Label { get; }
    public int DefaultSuspect { get; }
    public int DefaultCritical { get; }
    public DiagnosticDescriptor Suspect { get; }
    public DiagnosticDescriptor Critical { get; }

    private DiagnosticDescriptor Create(string id, string title, string description, string[] tags)
    {
        return new DiagnosticDescriptor(id, Label + ": " + title, MessageFormat, Category,
            DiagnosticSeverity.Info, true, description, customTags: tags);
    }
}

internal static class Rules
{
    public static readonly MetricRule Meloc = new MetricRule("meloc", "TT001", "TT101", 15, 25,
        "predugačka metoda",
        "Broj linija koda u telu metode, bez vitičastih zagrada koje otvaraju i zatvaraju telo, bez praznih linija i komentara. Kod metode napisane sa => broje se linije izraza.", false);

    public static readonly MetricRule Cyclo = new MetricRule("cyclo", "TT002", "TT102", 5, 12,
        "previše grananja u metodi",
        "Broj tačaka odlučivanja u metodi: if, while, for, foreach, switch (jednom, bez obzira na broj case-ova), continue, goto, uslovni izraz ?:, catch, logičko and/or (&&, ||, and, or) i ?? (i ??=), uvećan za 1. Metoda bez grananja ima 1.", false);

    public static readonly MetricRule Nop = new MetricRule("nop", "TT003", "TT103", 3, 6,
        "previše parametara",
        "Broj parametara koje metoda prima.", false);

    public static readonly MetricRule Cloc = new MetricRule("cloc", "TT004", "TT104", 80, 150,
        "prevelika klasa",
        "Broj linija koda u klasi, bez komentara i praznih linija.", false);

    public static readonly MetricRule Wmc = new MetricRule("wmc", "TT005", "TT105", 15, 25,
        "previše složenosti u klasi",
        "Zbir ciklomatske složenosti svih metoda u klasi.", false);

    public static readonly MetricRule Nad = new MetricRule("nad", "TT006", "TT106", 10, 15,
        "previše polja u klasi",
        "Broj atributa u klasi ili record-u: deklarisana polja, auto-property-ji ({ get; set; }) i parametri record-a, jer i oni čuvaju stanje objekta.", false);

    public static readonly MetricRule Nmd = new MetricRule("nmd", "TT007", "TT107", 12, 16,
        "previše metoda u klasi",
        "Broj deklarisanih metoda u klasi.", false);

    public static readonly MetricRule Cbo = new MetricRule("cbo", "TT008", "TT108", 8, 12,
        "previše zavisnosti",
        "Broj različitih klasa iz ovog projekta od kojih klasa zavisi: klase navedene u kodu i klase izraza koje klasa koristi, npr. rezultat poziva u lancu. Interfejsi, enum-i i tipovi iz .NET biblioteka se ne broje.", false);

    public static readonly MetricRule Dit = new MetricRule("dit", "TT009", "TT109", 3, 5,
        "preduboko nasleđivanje",
        "Broj predaka klase iz ovog projekta; bazne klase iz .NET biblioteka se ne broje. Prijavljuje se samo na najdubljoj klasi u lancu.", true);

    public static readonly DiagnosticDescriptor Measure = new DiagnosticDescriptor("TT000",
        "Izmerene vrednosti metrika", "{0} '{1}'", "Maintainability",
        DiagnosticSeverity.Info, true,
        "Sve izmerene vrednosti za metodu ili klasu. Prijavljuje se samo kada je build pokrenut sa TtMeasure=true.",
        customTags: new[] { WellKnownDiagnosticTags.CompilationEnd });

    public static readonly ImmutableArray<MetricRule> All =
        ImmutableArray.Create(Meloc, Cyclo, Nop, Cloc, Wmc, Nad, Nmd, Cbo, Dit);

    public static readonly ImmutableArray<DiagnosticDescriptor> Descriptors =
        All.SelectMany(r => new[] { r.Suspect, r.Critical }).Append(Measure).ToImmutableArray();
}
