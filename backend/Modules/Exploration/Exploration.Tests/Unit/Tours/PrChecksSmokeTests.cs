using Exploration.Domain.Tours;
using FluentAssertions;
using Shared.Tests;
using Xunit;

namespace Exploration.Tests.Unit.Tours;

public class PrChecksSmokeTests
{
    [Fact]
    public void New_tour_has_no_transport_times()
    {
        var tour = new Tour(WellKnownUsers.Explorer, "Probna tura", new string('o', 100), TourDifficulty.Easy, ["proba"]);

        tour.TransportTimes.Should().BeEmpty();
    }
}
