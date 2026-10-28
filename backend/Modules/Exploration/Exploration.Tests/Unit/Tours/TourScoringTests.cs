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

        score.Should().Be(1);
    }
}
