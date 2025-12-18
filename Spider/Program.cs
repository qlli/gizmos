using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;


namespace Spider
{
    public class GitHubRepository
    {
        [JsonPropertyName("full_name")]
        public string FullName { get; set; } = string.Empty;
        
        [JsonPropertyName("html_url")]
        public string HtmlUrl { get; set; } = string.Empty;
        
        [JsonPropertyName("stargazers_count")]
        public int StargazersCount { get; set; }
        
        [JsonPropertyName("forks_count")]
        public int ForksCount { get; set; }
        
        [JsonPropertyName("description")]
        public string Description { get; set; } = string.Empty;
    }



    public class GitHubSearchResponse
    {
        public int TotalCount { get; set; }
        public List<GitHubRepository> Items { get; set; } = new List<GitHubRepository>();
    }

    class Program
    {
        private static readonly HttpClient httpClient = new HttpClient();
        
        static async Task Main(string[] args)
        {
            Console.WriteLine("GitHub爬虫程序启动...");
            
            // 配置参数
            string keyword = "unreal";
            int minStars = 100;
            int maxResults = 10000;
            TimeSpan timeout = TimeSpan.FromMinutes(5);
            
            try
            {
                // 设置HTTP客户端超时
                httpClient.Timeout = timeout;
                
                // 设置User-Agent（GitHub API要求）
                httpClient.DefaultRequestHeaders.Add("User-Agent", "GitHub-Spider-App");
                
                var repositories = await SearchGitHubRepositories(keyword, minStars, maxResults, timeout);
                
                if (repositories.Count > 0)
                {
                    // 生成带时间戳的文件名
                    string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                    string csvFilename = $"github_repositories_{timestamp}.csv";
                    
                    await ExportToCsv(repositories, csvFilename);
                    Console.WriteLine($"成功抓取 {repositories.Count} 个仓库，已保存到 {csvFilename}");
                }

                else
                {
                    Console.WriteLine("未找到符合条件的仓库");
                }
            }
            catch (TaskCanceledException)
            {
                Console.WriteLine("爬虫超时，已中止执行");
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine($"HTTP请求错误: {ex.Message}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"发生错误: {ex.Message}");
            }
            
            Console.WriteLine("程序执行完毕");
        }

        static async Task<List<GitHubRepository>> SearchGitHubRepositories(string keyword, int minStars, int maxResults, TimeSpan timeout)
        {
            var repositories = new List<GitHubRepository>();
            int page = 1;
            const int perPage = 100; // GitHub API每页最大100条
            
            using var cts = new CancellationTokenSource(timeout);
            
            while (repositories.Count < maxResults)
            {
                try
                {
                    // 构建搜索URL - 使用正确的GitHub搜索语法
                    // 尝试不同的搜索策略：在名称、描述、主题中搜索unreal
                    string query = $"q=unreal+in:name,description,topic+stars:>{minStars}&sort=stars&order=desc&page={page}&per_page={perPage}";
                    string url = $"https://api.github.com/search/repositories?{query}";
                    
                    Console.WriteLine($"正在搜索第{page}页... URL: {url}");
                    
                    var response = await httpClient.GetAsync(url, cts.Token);
                    
                    if (!response.IsSuccessStatusCode)
                    {
                        Console.WriteLine($"HTTP错误: {response.StatusCode} - {response.ReasonPhrase}");
                        var errorContent = await response.Content.ReadAsStringAsync(cts.Token);
                        Console.WriteLine($"错误详情: {errorContent}");
                        
                        // 如果是速率限制，等待后重试
                        if (response.StatusCode == System.Net.HttpStatusCode.Forbidden)
                        {
                            Console.WriteLine("遇到速率限制，等待60秒后重试...");
                            await Task.Delay(60000, cts.Token);
                            continue;
                        }
                        break;
                    }
                    
                    var json = await response.Content.ReadAsStringAsync(cts.Token);
                    Console.WriteLine($"API响应JSON长度: {json.Length} 字符");
                    
                    // 调试：查看JSON的前500个字符
                    if (json.Length > 500)
                    {
                        Console.WriteLine($"JSON前500字符: {json.Substring(0, 500)}");
                    }
                    
                    try
                    {
                        var options = new JsonSerializerOptions
                        {
                            PropertyNameCaseInsensitive = true
                        };
                        var searchResponse = JsonSerializer.Deserialize<GitHubSearchResponse>(json, options);
                        
                        if (searchResponse == null)
                        {
                            Console.WriteLine("JSON反序列化失败，返回null");
                            break;
                        }
                        
                        if (searchResponse.Items == null || searchResponse.Items.Count == 0)
                        {
                            Console.WriteLine($"没有找到仓库，但API返回总数为: {searchResponse.TotalCount}");
                            break;
                        }
                        
                        Console.WriteLine($"本页找到 {searchResponse.Items.Count} 个仓库，总共 {searchResponse.TotalCount} 个结果");
                        
                        // 直接添加所有结果，因为GitHub API已经按条件过滤了
                        foreach (var repo in searchResponse.Items)
                        {
                            repositories.Add(repo);
                            Console.WriteLine($"找到仓库: {repo.FullName} (Stars: {repo.StargazersCount})");
                            
                            if (repositories.Count >= maxResults)
                            {
                                Console.WriteLine("已达到最大抓取数量限制");
                                break;
                            }
                        }
                        
                        page++;
                        
                        // GitHub API限制：短暂延迟避免速率限制
                        await Task.Delay(2000, cts.Token);
                    }
                    catch (JsonException ex)
                    {
                        Console.WriteLine($"JSON反序列化错误: {ex.Message}");
                        Console.WriteLine("尝试查看JSON结构...");
                        if (json.Contains("items"))
                        {
                            Console.WriteLine("JSON包含items字段，但反序列化失败");
                        }
                        break;
                    }
                }
                catch (OperationCanceledException) when (cts.Token.IsCancellationRequested)
                {
                    Console.WriteLine("搜索操作被取消");
                    break;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"搜索过程中发生异常: {ex.Message}");
                    break;
                }
            }
            
            return repositories;
        }




        static async Task ExportToCsv(List<GitHubRepository> repositories, string filename)
        {
            using var writer = new StreamWriter(filename, false, System.Text.Encoding.UTF8);
            
            // 写入CSV头部（添加BOM以确保Excel正确识别UTF-8编码）
            writer.Write('\uFEFF'); // UTF-8 BOM
            await writer.WriteLineAsync("仓库名称,GitHub地址,Star数量,Fork数量,仓库说明");
            
            // 写入数据
            foreach (var repo in repositories)
            {
                // 处理CSV特殊字符和长文本
                string description = repo.Description ?? "";
                
                // 清理描述文本：移除所有控制字符和不可打印字符
                description = new string(description.Where(c => !char.IsControl(c)).ToArray());
                
                // 清理描述文本：移除换行符和制表符
                description = description.Replace("\r\n", " ").Replace("\n", " ").Replace("\t", " ");
                
                // 限制描述长度，避免CSV文件过大
                if (description.Length > 200)
                {
                    description = description.Substring(0, 200) + "...";
                }
                
                // 处理CSV特殊字符 - 总是用引号包裹描述字段
                description = description.Replace("\"", "\"\""); // 转义引号
                description = $"\"{description}\"";
                
                // 处理仓库名称
                string fullName = repo.FullName ?? "";
                if (fullName.Contains(",") || fullName.Contains("\"") || fullName.Contains("\n") || fullName.Contains("\r"))
                {
                    fullName = fullName.Replace("\"", "\"\"");
                    fullName = $"\"{fullName}\"";
                }
                
                await writer.WriteLineAsync($"{fullName},{repo.HtmlUrl},{repo.StargazersCount},{repo.ForksCount},{description}");
            }

        }



    }
}