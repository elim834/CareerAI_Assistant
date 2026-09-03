using System.Windows;
using System.Windows.Controls;
using frontend.Services;

namespace frontend
{
    public partial class FacultyResearchWindow : Window
    {
        private readonly ApiClient _api = new ApiClient();

        public FacultyResearchWindow()
        {
            InitializeComponent();
        }

        private async void SearchButton_Click(object sender, RoutedEventArgs e)
        {
            string query = QueryTextBox.Text.Trim();
            if (string.IsNullOrEmpty(query))
            {
                StatusText.Text = "⚠️ Please enter a professor or lab name first.";
                return;
            }

            SearchButton.IsEnabled = false;
            ResultPanel.Visibility = Visibility.Collapsed;
            StatusText.Text = "Searching (this can take a few seconds)...";

            try
            {
                var result = await _api.SearchFacultyResearchAsync(query);
                if (result == null)
                {
                    StatusText.Text = "❌ Could not find or summarize research for this query.";
                    return;
                }

                ResearcherNameText.Text = result.ResearcherName ?? query;
                SummaryText.Text = result.Summary ?? "—";
                TopicsList.ItemsSource = result.RecentTopics ?? new List<string>();
                SourcesList.ItemsSource = result.Sources ?? new List<string>();

                StatusText.Text = "";
                ResultPanel.Visibility = Visibility.Visible;
            }
            catch (Exception ex)
            {
                StatusText.Text = $"❌ Search failed: {ex.Message}";
            }
            finally
            {
                SearchButton.IsEnabled = true;
            }
        }
    }
}