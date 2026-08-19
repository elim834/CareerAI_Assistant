using System.Windows;
using Microsoft.Win32;
using frontend.Services;
namespace frontend
{
    public partial class MainWindow : Window
    {
        private readonly ApiClient _api = new ApiClient();

        public MainWindow()
        {
            InitializeComponent();
            Loaded += MainWindow_Loaded;
        }

        private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            try
            {
                bool isRunning = await _api.IsServerRunningAsync();
                if (!isRunning)
                {
                    StatusText.Text = "❌ Backend is not running. Start main.py first.";
                    return;
                }

                var applications = await _api.GetApplicationsAsync();
                StatusText.Text = $"✅ Connected. {applications.Count} application(s) found.";
                ApplicationsGrid.ItemsSource = applications;
            }
            catch (Exception ex)
            {
                StatusText.Text = $"❌ Startup error: {ex.Message}";
            }
        }
        private async void ApplicationsGrid_MouseDoubleClick(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            if (ApplicationsGrid.SelectedItem is not frontend.Models.ApplicationDto selected)
                return;

            try
            {
                StatusText.Text = $"Analyzing \"{selected.Program}\"...";

                var analysis = await _api.AnalyzeApplicationAsync(selected.Id);
                if (analysis == null)
                {
                    StatusText.Text = "❌ Analysis failed. Check backend logs.";
                    return;
                }

                MessageBox.Show(
                    $"Score: {analysis.AcceptanceScore}/10\n\n" +
                    $"Reasoning: {analysis.Reasoning}\n\n" +
                    $"Visa: {analysis.VisaSummary}\n\n" +
                    $"Suggested focus: {analysis.SuggestedFocus}",
                    $"Analysis — {selected.University}",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);

                var applications = await _api.GetApplicationsAsync();
                ApplicationsGrid.ItemsSource = applications;
                StatusText.Text = $"✅ Connected. {applications.Count} application(s) found.";
            }
            catch (Exception ex)
            {
                StatusText.Text = $"❌ Analysis failed: {ex.Message}";
            }
        }        
        private async void UploadTranscriptButton_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog { Filter = "PDF files (*.pdf)|*.pdf" };
            if (dialog.ShowDialog() != true) return;

            try
            {
                StatusText.Text = "Uploading transcript...";
                var result = await _api.UploadTranscriptAsync(dialog.FileName);
                StatusText.Text = $"✅ Transcript processed: {result}";
            }
            catch (Exception ex)
            {
                StatusText.Text = $"❌ Upload failed: {ex.Message}";
            }
        }
        private async void UploadCvButton_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog { Filter = "PDF files (*.pdf)|*.pdf" };
            if (dialog.ShowDialog() != true) return;

            try
            {
                StatusText.Text = "Uploading CV...";
                var result = await _api.UploadCvAsync(dialog.FileName);
                StatusText.Text = $"✅ CV processed: {result}";
            }
            catch (Exception ex)
            {
                StatusText.Text = $"❌ Upload failed: {ex.Message}";
            }
        }        
        private async void ScanUrlButton_Click(object sender, RoutedEventArgs e)
        {
            string url = ScanUrlTextBox.Text.Trim();
            if (string.IsNullOrEmpty(url))
            {
                StatusText.Text = "⚠️ Please enter a URL first.";
                return;
            }

            try
            {
                StatusText.Text = "Scanning URL (this can take a few seconds)...";
                ScanUrlButton.IsEnabled = false;

                await _api.ScanUrlAsync(url);

                var applications = await _api.GetApplicationsAsync();
                ApplicationsGrid.ItemsSource = applications;
                StatusText.Text = $"✅ Scan complete. {applications.Count} application(s) total.";
                ScanUrlTextBox.Text = "";
            }
            catch (Exception ex)
            {
                StatusText.Text = $"❌ Scan failed: {ex.Message}";
            }
            finally
            {
                ScanUrlButton.IsEnabled = true;
            }
        }    }
}