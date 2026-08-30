namespace frontend.Models
{
    public class ApplicationDto
    {
        public int Id { get; set; }
        public string? Country { get; set; }
        public string? University { get; set; }
        public string? Program { get; set; }
        public string? ScholarshipAmount { get; set; }
        public string? Tuition { get; set; }
        public double? GpaRequirement { get; set; }
        public double? ToeflRequirement { get; set; }
        public string? Deadline { get; set; }
        public string? VisaCountry { get; set; }
        public string? SubRole { get; set; }
        public double? AcceptanceScore { get; set; }
        public string? Status { get; set; }
        public string? Notes { get; set; }
        public string? LabFitParagraph { get; set; }
        public string? LanguageRequirementStatus { get; set; }
        public string? ApplicationType { get; set; }

        // Computed, not from JSON — used for countdown display and color coding
        public int? DaysLeft
        {
            get
            {
                if (string.IsNullOrWhiteSpace(Deadline)) return null;
                if (!DateTime.TryParse(Deadline, out var deadlineDate)) return null;
                return (deadlineDate.Date - DateTime.Today).Days;
            }
        }

        public string DaysLeftDisplay
        {
            get
            {
                if (DaysLeft == null) return "—";
                if (DaysLeft < 0) return "Passed";
                if (DaysLeft == 0) return "Today!";
                return $"{DaysLeft} day(s)";
            }
        }
    }
}