using Exploration.Domain.Tours;
using FluentAssertions;
using Xunit;

namespace Exploration.Tests.Unit.Tours;

public class TourScoringTests
{
    [Fact]
    public void Empty_tour_scores_zero()
    {
        var score = TourScoring.Score(0, 0, 0, 0, false, false, false);

        score.Should().Be(0);
    }

    [Fact]
    public void Long_popular_guided_tour_in_winter_night_scores_eight()
    {
        var score = TourScoring.Score(25, 9, 11, 101, true, true, true);

        score.Should().Be(8);
    }

    [Fact]
    public void Medium_tour_scores_five()
    {
        var score = TourScoring.Score(15, 5, 6, 0, false, false, false);

        score.Should().Be(5);
    }

    [Fact]
    public void Short_tour_scores_one()
    {
        var score = TourScoring.Score(5, 1, 1, 0, false, false, false);

        score.Should().Be(1);
    }

    [Fact]
    public void Score_never_drops_below_zero()
    {
        var score = TourScoring.Score(0, 0, 0, 0, false, true, false);

        score.Should().Be(0);
    }
}
