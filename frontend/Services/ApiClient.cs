using System;
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
            _http = new HttpClient
            {
                BaseAddress = new Uri(BaseUrl) };
            
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
            using var cts = new CancellationTokenSource(TimeSpan.FromMinutes(3));
            var response = await _http.PostAsJsonAsync("/scan-url", payload);

            return await response.Content.ReadAsStringAsync();
        }
        
        public async Task<bool> UpdateSubRoleAsync(int applicationId, string subRole)
        {
            var payload = new { sub_role = subRole };
            var response = await _http.PatchAsJsonAsync($"/applications/{applicationId}/sub-role", payload);
            return response.IsSuccessStatusCode;
        }
        
        public async Task<bool> UpdateStatusAsync(int applicationId, string status)
        {
            var payload = new { status = status };
            var response = await _http.PatchAsJsonAsync($"/applications/{applicationId}/status", payload);
            return response.IsSuccessStatusCode;
        }
        
        public async Task<bool> DeleteApplicationAsync(int applicationId)
        {
            var response = await _http.DeleteAsync($"/applications/{applicationId}");
            return response.IsSuccessStatusCode;
        }
        
        public async Task<ProfileDto?> GetProfileAsync()
        {
            var response = await _http.GetAsync("/profile");
            if (!response.IsSuccessStatusCode) return null;
            var json = await response.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<ProfileDto>(json, _jsonOptions);
        }
        
        public async Task<LastAnalysisResponse?> GetLastAnalysisAsync(int applicationId)
        {
            var response = await _http.GetAsync($"/applications/{applicationId}/last-analysis");
            if (!response.IsSuccessStatusCode)
                return null;

            var json = await response.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<LastAnalysisResponse>(json, _jsonOptions);
        }
        
        public async Task<CoverLetterDto?> GenerateCoverLetterAsync(int applicationId, string? facultyQuery = null)
        {
            var payload = new { faculty_query = facultyQuery };
            var response = await _http.PostAsJsonAsync($"/cover-letter/{applicationId}", payload);
            if (!response.IsSuccessStatusCode)
                return null;

            var json = await response.Content.ReadAsStringAsync();
            var result = JsonSerializer.Deserialize<CoverLetterResponse>(json, _jsonOptions);
            return result?.Letter;
        }    
        
        public async Task<FacultyResearchDto?> SearchFacultyResearchAsync(string query)
        {
            var payload = new { query = query };
            var response = await _http.PostAsJsonAsync("/faculty-research/search", payload);
            if (!response.IsSuccessStatusCode)
                return null;

            var json = await response.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<FacultyResearchDto>(json, _jsonOptions);
        }
        
    }
}