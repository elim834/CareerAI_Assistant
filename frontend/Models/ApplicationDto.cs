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
    }
}