namespace frontend.Models
{
    public class CoverLetterResponse
    {
        public int ApplicationId { get; set; }
        public CoverLetterDto? Letter { get; set; }
    }

    public class CoverLetterDto
    {
        public string? OpeningParagraph { get; set; }
        public string? BodyParagraph { get; set; }
        public string? LabFitParagraph { get; set; }
        public string? ClosingParagraph { get; set; }
        public List<string>? KeyPointsToExpand { get; set; }
    }
}