namespace Exploration.Domain.Tours;

public static class TourScoring
{
    public static int Score(int distanceKm, int durationHours, int keyPoints, int reviews, bool hasGuide, bool isNight, bool isWinter)
    {
        var score = 0

        if (distanceKm > 20)
            score += 3;
        else if (distanceKm > 10)
            score += 2;
        else if (distanceKm > 0)
            score += 1;

        if (durationHours > 8)
            score += 3;
        else if (durationHours > 4)
            score += 2;

        if (keyPoints > 10)
            score += 2;
        else if (keyPoints > 5)
            score += 1;

        if (reviews > 100)
            score += 2;

        if (hasGuide && reviews > 10)
            score += 1;

        if (isNight)
            score -= 1;

        if (isWinter)
            score -= 1;

        if (isNight && isWinter)
            score -= 1;

        return score < 0 ? 0 : score;
    }
}
