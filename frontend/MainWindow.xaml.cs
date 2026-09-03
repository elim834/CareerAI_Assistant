using System.Windows;
using Microsoft.Win32;
using frontend.Services;
using ClosedXML.Excel;
using System.Linq;
using System.Text.Json;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;


namespace frontend
{
    public partial class MainWindow : Window
    {
        private readonly ApiClient _api = new ApiClient();
        private List<frontend.Models.ApplicationDto> _allApplications = new();

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
                _allApplications = applications;
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
                StatusText.Text = $"Loading \"{selected.Program}\"...";

                var lastAnalysisResponse = await _api.GetLastAnalysisAsync(selected.Id);
                var analysis = lastAnalysisResponse?.Analysis; // may be null if never analyzed

                var detailWindow = new DetailWindow(selected, analysis, _api) { Owner = this };
                detailWindow.ShowDialog();

                if (detailWindow.WasDeleted)
                {
                    StatusText.Text = "Application deleted.";
                }

                var applications = await _api.GetApplicationsAsync();
                _allApplications = applications;
                ApplicationsGrid.ItemsSource = applications;
                StatusText.Text = $"✅ Connected. {applications.Count} application(s) found.";
            }
            catch (Exception ex)
            {
                StatusText.Text = $"❌ Failed to load: {ex.Message}";
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
                _allApplications = applications;
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
        }
        
        private void ExportButton_Click(object sender, RoutedEventArgs e)
{
    if (ApplicationsGrid.ItemsSource is not System.Collections.Generic.List<frontend.Models.ApplicationDto> applications
        || applications.Count == 0)
    {
        StatusText.Text = "⚠️ No data to export.";
        return;
    }

    var saveDialog = new SaveFileDialog
    {
        Filter = "Excel files (*.xlsx)|*.xlsx",
        FileName = "CareerAI_Applications.xlsx"
    };
    if (saveDialog.ShowDialog() != true) return;

    try
    {
        using var workbook = new XLWorkbook();
        var sheet = workbook.Worksheets.Add("Applications");

        string[] headers = { "Country", "University", "Program", "Scholarship", "Tuition",
            "GPA Req.", "TOEFL Req.", "Deadline", "Visa Country", "Sub Role",
            "Score", "Status", "Notes" };

        for (int i = 0; i < headers.Length; i++)
            sheet.Cell(1, i + 1).Value = headers[i];

        int row = 2;
        foreach (var app in applications)
        {
            sheet.Cell(row, 1).Value = app.Country ?? "";
            sheet.Cell(row, 2).Value = app.University ?? "";
            sheet.Cell(row, 3).Value = app.Program ?? "";
            sheet.Cell(row, 4).Value = app.ScholarshipAmount ?? "";
            sheet.Cell(row, 5).Value = app.Tuition ?? "";
            sheet.Cell(row, 6).Value = app.GpaRequirement?.ToString() ?? "";
            sheet.Cell(row, 7).Value = app.ToeflRequirement?.ToString() ?? "";
            sheet.Cell(row, 8).Value = app.Deadline ?? "";
            sheet.Cell(row, 9).Value = app.VisaCountry ?? "";
            sheet.Cell(row, 10).Value = app.SubRole ?? "";
            sheet.Cell(row, 11).Value = app.AcceptanceScore?.ToString() ?? "";
            sheet.Cell(row, 12).Value = app.Status ?? "";
            sheet.Cell(row, 13).Value = app.Notes ?? "";
            row++;
        }

        // Enable text wrapping so long text doesn't get cut off, and auto-fit row heights
        var usedRange = sheet.RangeUsed();
        if (usedRange != null)
        {
            usedRange.Style.Alignment.WrapText = true;
            usedRange.Style.Alignment.Vertical = XLAlignmentVerticalValues.Top;
        }

        sheet.Columns().AdjustToContents();

        // Cap column widths so a single long cell doesn't stretch the whole sheet
        foreach (var column in sheet.ColumnsUsed())
        {
            if (column.Width > 50) column.Width = 50;
        }

        sheet.Rows().AdjustToContents();
        
        // Configure the page so all 13 columns fit on one page width when printed/viewed
        sheet.PageSetup.PageOrientation = XLPageOrientation.Landscape;
        sheet.PageSetup.PagesWide = 1;
        sheet.PageSetup.PagesTall = 0; // 0 = auto (as many pages tall as needed)
        sheet.PageSetup.Margins.Left = 0.3;
        sheet.PageSetup.Margins.Right = 0.3;
        sheet.PageSetup.Margins.Top = 0.4;
        sheet.PageSetup.Margins.Bottom = 0.4;

        // Freeze the header row so it stays visible while scrolling
        sheet.SheetView.FreezeRows(1);
        
        workbook.SaveAs(saveDialog.FileName);

        StatusText.Text = $"✅ Exported {applications.Count} application(s) to Excel.";
    }
    catch (Exception ex)
    {
        StatusText.Text = $"❌ Export failed: {ex.Message}";
    }
}
        
        private void KanbanButton_Click(object sender, RoutedEventArgs e)
        {
            if (ApplicationsGrid.ItemsSource is not List<frontend.Models.ApplicationDto> applications)
            {
                StatusText.Text = "⚠️ No data loaded yet.";
                return;
            }

            var kanban = new KanbanWindow(_api, applications) { Owner = this };
            kanban.ShowDialog();
        }

        private void ShowAllButton_Click(object sender, RoutedEventArgs e)
        {
            ApplicationsGrid.ItemsSource = _allApplications;
        }

        private void ShowMastersButton_Click(object sender, RoutedEventArgs e)
        {
            ApplicationsGrid.ItemsSource = _allApplications
                .Where(a => a.ApplicationType == "masters" || a.ApplicationType == null)
                .ToList();
        }
        
        private void OpenDetail_Click(object sender, RoutedEventArgs e)
        {
            if (ApplicationsGrid.SelectedItem is frontend.Models.ApplicationDto selected)
            {
                // Reuse the existing double-click flow
                ApplicationsGrid_MouseDoubleClick(sender, null!);
            }
        }

        private async void DeleteRow_Click(object sender, RoutedEventArgs e)
        {
            if (ApplicationsGrid.SelectedItem is not frontend.Models.ApplicationDto selected)
                return;

            var result = MessageBox.Show(
                $"Are you sure you want to delete \"{selected.University} — {selected.Program}\"?",
                "Confirm Deletion",
                MessageBoxButton.YesNo,
                MessageBoxImage.Warning);

            if (result != MessageBoxResult.Yes) return;

            try
            {
                StatusText.Text = "Deleting...";
                var success = await _api.DeleteApplicationAsync(selected.Id);
                if (!success)
                {
                    StatusText.Text = "❌ Delete operation failed.";
                    return;
                }

                var applications = await _api.GetApplicationsAsync();
                _allApplications = applications;
                ApplicationsGrid.ItemsSource = applications;
                StatusText.Text = $"🗑️ Deleted. {applications.Count} application(s) remaining.";
            }
            catch (Exception ex)
            {
                StatusText.Text = $"❌ Delete error: {ex.Message}";
            }
        }

        private void ShowInternshipsButton_Click(object sender, RoutedEventArgs e)
        {
            ApplicationsGrid.ItemsSource = _allApplications
                .Where(a => a.ApplicationType == "internship")
                .ToList();
        }
        
        private void HomeButton_Click(object sender, RoutedEventArgs e)
        {
            var dashboard = new DashboardWindow();
            dashboard.Show();
            Close();
        }
        private void FacultyResearchButton_Click(object sender, RoutedEventArgs e)
        {
            var window = new FacultyResearchWindow();
            window.Show();
        }
        
        private void ApplicationsGrid_PreviewMouseRightButtonDown(object sender, MouseButtonEventArgs e)
        {
            var dep = (DependencyObject)e.OriginalSource;
            while (dep != null && dep is not DataGridRow)
            {
                dep = VisualTreeHelper.GetParent(dep);
            }

            if (dep is DataGridRow row)
            {
                row.IsSelected = true;
                ApplicationsGrid.SelectedItem = row.Item;
            }
        }
        
    }
}