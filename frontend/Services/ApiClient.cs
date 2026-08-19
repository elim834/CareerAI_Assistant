using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using frontend.Models;

namespace frontend.Services
{
    public class ApiClient
    {
        private readonly HttpClient _http;
        private const string BaseUrl = "http://127.0.0.1:8000";

        public ApiClient()
        {
            _http = new HttpClient { BaseAddress = new Uri(BaseUrl) };
        }

        private readonly JsonSerializerOptions _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
        };

        public async Task<List<ApplicationDto>> GetApplicationsAsync()
        {
            var response = await _http.GetAsync("/applications");
            response.EnsureSuccessStatusCode();

            var json = await response.Content.ReadAsStringAsync();
            var result = JsonSerializer.Deserialize<List<ApplicationDto>>(json, _jsonOptions);
            return result ?? new List<ApplicationDto>();
        }

        public async Task<bool> IsServerRunningAsync()
        {
            try
            {
                var response = await _http.GetAsync("/");
                return response.IsSuccessStatusCode;
            }
            catch (HttpRequestException)
            {
                return false;
            }
        }
        public async Task<AnalysisDto?> AnalyzeApplicationAsync(int applicationId)
        {
            var response = await _http.PostAsync($"/analyze/{applicationId}", null);
            if (!response.IsSuccessStatusCode)
                return null;

            var json = await response.Content.ReadAsStringAsync();
            var result = JsonSerializer.Deserialize<AnalysisResponse>(json, _jsonOptions);
            return result?.Analysis;
        }
        
        public async Task<string> UploadTranscriptAsync(string filePath)
        {
            using var form = new MultipartFormDataContent();
            using var fileStream = File.OpenRead(filePath);
            using var fileContent = new StreamContent(fileStream);
            fileContent.Headers.ContentType = new MediaTypeHeaderValue("application/pdf");
            form.Add(fileContent, "file", Path.GetFileName(filePath));

            var response = await _http.PostAsync("/profile/upload-pdf", form);
            return await response.Content.ReadAsStringAsync();
        }

        public async Task<string> UploadCvAsync(string filePath)
        {
            using var form = new MultipartFormDataContent();
            using var fileStream = File.OpenRead(filePath);
            using var fileContent = new StreamContent(fileStream);
            fileContent.Headers.ContentType = new MediaTypeHeaderValue("application/pdf");
            form.Add(fileContent, "file", Path.GetFileName(filePath));

            var response = await _http.PostAsync("/profile/upload-cv", form);
            return await response.Content.ReadAsStringAsync();
        }
        
        public async Task<string> ScanUrlAsync(string url)
        {
            var payload = new { url = url };
            var response = await _http.PostAsJsonAsync("/scan-url", payload);
            return await response.Content.ReadAsStringAsync();
        }
    }
}