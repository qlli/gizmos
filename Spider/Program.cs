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
        private static CancellationTokenSource globalCts = new CancellationTokenSource();
        
        static async Task Main(string[] args)
        {
            Console.WriteLine("请选择爬虫类型：");
            Console.WriteLine("1. GitHub仓库爬虫");
            Console.WriteLine("2. YouTube视频爬虫");
            Console.Write("请输入选择（1或2）：");
            
            var choice = Console.ReadLine();
            
            // 取消之前可能正在运行的爬虫程序
            if (!globalCts.IsCancellationRequested)
            {
                globalCts.Cancel();
                Console.WriteLine("正在停止之前运行的爬虫程序...");
                await Task.Delay(1000); // 给之前的爬虫程序一点时间清理
            }
            
            // 创建新的CancellationTokenSource用于当前爬虫
            globalCts = new CancellationTokenSource();
            
            switch (choice)
            {
                case "1":
                    await RunGitHubSpider(globalCts.Token);
                    break;
                case "2":
                    await YouTubeSpider.RunAsync(globalCts.Token);
                    break;
                default:
                    Console.WriteLine("无效选择，默认运行GitHub爬虫");
                    await RunGitHubSpider(globalCts.Token);
                    break;
            }
        }
        
        static async Task RunGitHubSpider(CancellationToken cancellationToken)
        {
            Console.WriteLine("GitHub爬虫程序启动...");
            
            // 检查是否已被取消
            if (cancellationToken.IsCancellationRequested)
            {
                Console.WriteLine("爬虫程序已被取消");
                return;
            }
            
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
                
                var repositories = await SearchGitHubRepositories(keyword, minStars, maxResults, timeout, cancellationToken);
                
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
            
            Console.WriteLine("GitHub爬虫程序执行完毕");
        }

        static async Task<List<GitHubRepository>> SearchGitHubRepositories(string keyword, int minStars, int maxResults, TimeSpan timeout, CancellationToken cancellationToken)
        {
            var repositories = new List<GitHubRepository>();
            int page = 1;
            const int perPage = 100; // GitHub API每页最大100条
            
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            cts.CancelAfter(timeout);
            
            while (repositories.Count < maxResults)
            {
                try
                {
                    // 检查是否已被取消
                    if (cts.Token.IsCancellationRequested)
                    {
                        Console.WriteLine("搜索操作被用户取消");
                        break;
                    }
                    
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

// YouTube视频数据模型
public class YouTubeVideo
{
    public string Title { get; set; } = string.Empty;
    public string VideoUrl { get; set; } = string.Empty;
    public string ChannelName { get; set; } = string.Empty;
    public long LikeCount { get; set; }
    public DateTime PublishedAt { get; set; }
    public string Description { get; set; } = string.Empty;
}

// YouTube爬虫类
public static class YouTubeSpider
{
    private static readonly HttpClient httpClient = new HttpClient();
    
    public static async Task RunAsync(CancellationToken cancellationToken)
    {
        Console.WriteLine("YouTube爬虫程序启动...");
        
        // 检查是否已被取消
        if (cancellationToken.IsCancellationRequested)
        {
            Console.WriteLine("爬虫程序已被取消");
            return;
        }
        
        // 配置参数 - 大幅降低要求
        string keyword = "GPU";
        long minLikes = 0; // 取消点赞数限制
        int maxResults = 10; // 只抓取10条
        TimeSpan timeout = TimeSpan.FromMinutes(5);
        DateTime threeYearsAgo = DateTime.Now.AddYears(-10); // 取消时间限制
        
        try
        {
            // 设置HTTP客户端超时
            httpClient.Timeout = timeout;
            
            // 设置User-Agent
            httpClient.DefaultRequestHeaders.Add("User-Agent", "YouTube-Spider-App");
            
            var videos = await SearchYouTubeVideos(keyword, minLikes, threeYearsAgo, maxResults, timeout, cancellationToken);
            
            if (videos.Count > 0)
            {
                // 生成带时间戳的文件名
                string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                string csvFilename = $"youtube_videos_{timestamp}.csv";
                
                await ExportToCsv(videos, csvFilename);
                Console.WriteLine($"成功抓取 {videos.Count} 个视频，已保存到 {csvFilename}");
            }
            else
            {
                Console.WriteLine("未找到符合条件的视频");
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
        
        Console.WriteLine("YouTube爬虫程序执行完毕");
    }
    
    static async Task<List<YouTubeVideo>> SearchYouTubeVideos(string keyword, long minLikes, DateTime minDate, int maxResults, TimeSpan timeout, CancellationToken cancellationToken)
    {
        var videos = new List<YouTubeVideo>();
        
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        cts.CancelAfter(timeout);
        
        try
        {
            // 检查是否已被取消
            if (cts.Token.IsCancellationRequested)
            {
                Console.WriteLine("搜索操作被用户取消");
                return videos;
            }
            
            // YouTube Data API需要有效的API密钥
            string apiKey = GetYouTubeApiKey();
            
            // 如果是演示模式，使用模拟数据
            if (apiKey == "DEMO_MODE")
            {
                Console.WriteLine("🔧 演示模式：使用模拟GPU相关视频数据");
                return GetDemoYouTubeVideos();
            }
            
            if (string.IsNullOrEmpty(apiKey))
            {
                Console.WriteLine("错误：API密钥为空");
                return videos;
            }
            
            Console.WriteLine($"🔑 使用的API密钥: {apiKey.Substring(0, 10)}...");
            
            // 检查是否是演示模式
            if (apiKey == "DEMO_MODE")
            {
                Console.WriteLine("🔧 演示模式：使用模拟GPU相关视频数据");
                return GetDemoYouTubeVideos();
            }

            
            Console.WriteLine($"✅ 开始使用YouTube API搜索视频，关键词: {keyword}");
            
            // 放宽搜索条件：尝试多个相关关键词
            string[] searchKeywords = new[] {
                "GPU tutorial",
                "GPU programming",
                "CUDA tutorial", 
                "显卡教程",
                "GPU 教学"
            };
            
            foreach (var searchKeyword in searchKeywords)
            {
                if (videos.Count >= 10) break; // 达到10条就停止
                
                Console.WriteLine($"尝试搜索关键词: {searchKeyword}");
                
                // 搜索参数 - 放宽条件
                int maxApiResults = 10; // 每次只取10条
                string searchUrl = $"https://www.googleapis.com/youtube/v3/search?part=snippet&q={Uri.EscapeDataString(searchKeyword)}&type=video&maxResults={maxApiResults}&order=relevance&key={apiKey}";
                
                Console.WriteLine($"搜索URL: {searchUrl}");
                
                var searchResponse = await httpClient.GetAsync(searchUrl, cts.Token);
                
                if (!searchResponse.IsSuccessStatusCode)
                {
                    Console.WriteLine($"YouTube API错误: {searchResponse.StatusCode} - {searchResponse.ReasonPhrase}");
                    var errorContent = await searchResponse.Content.ReadAsStringAsync(cts.Token);
                    Console.WriteLine($"错误详情: {errorContent}");
                    
                    // 如果是配额问题，直接返回
                    if (errorContent.Contains("quotaExceeded") || errorContent.Contains("quota"))
                    {
                        Console.WriteLine("API配额已用完，无法继续搜索");
                        break;
                    }
                    continue;
                }
                
                var searchJson = await searchResponse.Content.ReadAsStringAsync(cts.Token);
                
                Console.WriteLine($"🔍 API响应长度: {searchJson.Length} 字符");
                
                // 检查响应是否包含错误信息
                if (searchJson.Contains("error") || searchJson.Contains("Error"))
                {
                    Console.WriteLine($"❌ API返回错误响应: {searchJson}");
                    continue;
                }
                
                // 解析搜索响应
                try
                {
                    using var searchDoc = JsonDocument.Parse(searchJson);
                    
                    // 检查是否有items字段
                    if (!searchDoc.RootElement.TryGetProperty("items", out var itemsElement))
                    {
                        Console.WriteLine("❌ API响应中没有找到items字段");
                        Console.WriteLine($"响应预览: {searchJson.Substring(0, Math.Min(500, searchJson.Length))}...");
                        continue;
                    }
                    
                    Console.WriteLine($"✅ 找到 {itemsElement.GetArrayLength()} 个视频项目");
                    
                    // 处理找到的视频项目
                    foreach (var item in itemsElement.EnumerateArray())
                    {
                        try
                        {
                            var video = ParseYouTubeVideo(item);
                            if (video != null)
                            {
                                videos.Add(video);
                                Console.WriteLine($"📹 已添加视频: {video.Title}");
                                
                                // 达到10条限制就停止
                                if (videos.Count >= 10)
                                {
                                    Console.WriteLine("✅ 已达到10条视频限制，停止搜索");
                                    return videos;
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"⚠️  解析单个视频时出错: {ex.Message}");
                        }
                    }
                }
                catch (JsonException jsonEx)
                {
                    Console.WriteLine($"❌ JSON解析错误: {jsonEx.Message}");
                    Console.WriteLine($"响应内容: {searchJson.Substring(0, Math.Min(200, searchJson.Length))}");
                    continue;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"❌ 解析响应时发生错误: {ex.Message}");
                    continue;
                }

                Console.WriteLine($"找到 {videos.Count} 个视频，继续搜索...");

                
                // 获取视频详细信息
                var videoIds = new List<string>();
                foreach (var item in items.EnumerateArray())
                {
                    if (item.TryGetProperty("id", out var idElement) && idElement.TryGetProperty("videoId", out var videoId))
                    {
                        videoIds.Add(videoId.GetString());
                    }
                }
                
                if (videoIds.Count == 0)
                {
                    Console.WriteLine("未找到有效的视频ID");
                    continue;
                }
                
                // 批量获取视频统计信息
                string videoIdsParam = string.Join(",", videoIds.Take(10)); // 限制每次最多10个
                string statsUrl = $"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={videoIdsParam}&key={apiKey}";
                
                var statsResponse = await httpClient.GetAsync(statsUrl, cts.Token);
                
                if (!statsResponse.IsSuccessStatusCode)
                {
                    Console.WriteLine($"YouTube视频统计API错误: {statsResponse.StatusCode}");
                    continue;
                }
                
                var statsJson = await statsResponse.Content.ReadAsStringAsync(cts.Token);
                
                // 解析视频详细信息
                using var statsDoc = JsonDocument.Parse(statsJson);
                
                if (!statsDoc.RootElement.TryGetProperty("items", out var videoItems))
                {
                    Console.WriteLine("视频统计API响应中没有找到items字段");
                    continue;
                }
                
                foreach (var videoItem in videoItems.EnumerateArray())
                {
                    if (cts.Token.IsCancellationRequested)
                    {
                        Console.WriteLine("视频处理被取消");
                        break;
                    }
                    
                    try
                    {
                        var snippet = videoItem.GetProperty("snippet");
                        var statistics = videoItem.GetProperty("statistics");
                        
                        string title = snippet.GetProperty("title").GetString() ?? "";
                        string videoId = videoItem.GetProperty("id").GetString() ?? "";
                        string channelName = snippet.GetProperty("channelTitle").GetString() ?? "";
                        string description = snippet.GetProperty("description").GetString() ?? "";
                        
                        // 解析发布时间
                        DateTime publishedAt = DateTime.Parse(snippet.GetProperty("publishedAt").GetString());
                        
                        // 解析点赞数 - 放宽条件，只要有点赞数就接受
                        long likeCount = 0;
                        if (statistics.TryGetProperty("likeCount", out var likeCountElement))
                        {
                            long.TryParse(likeCountElement.GetString(), out likeCount);
                        }
                        
                        // 放宽过滤条件：只要有GPU相关关键词就接受
                        bool isGpuRelated = title.ToLower().Contains("gpu") || 
                                          title.ToLower().Contains("显卡") ||
                                          title.ToLower().Contains("cuda") ||
                                          description.ToLower().Contains("gpu") ||
                                          description.ToLower().Contains("显卡") ||
                                          description.ToLower().Contains("cuda");
                        
                        if (isGpuRelated)
                        {
                            var video = new YouTubeVideo
                            {
                                Title = title,
                                VideoUrl = $"https://www.youtube.com/watch?v={videoId}",
                                ChannelName = channelName,
                                LikeCount = likeCount,
                                PublishedAt = publishedAt,
                                Description = description
                            };
                            
                            videos.Add(video);
                            Console.WriteLine($"✅ 找到GPU相关视频: {title} (点赞: {likeCount}, 发布时间: {publishedAt:yyyy-MM-dd})");
                            
                            if (videos.Count >= 10)
                            {
                                Console.WriteLine("已达到目标数量10条");
                                return videos;
                            }
                        }
                        else
                        {
                            Console.WriteLine($"❌ 跳过非GPU相关视频: {title}");
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"解析视频信息时出错: {ex.Message}");
                        continue;
                    }
                }
                
                // 避免API速率限制
                await Task.Delay(2000, cts.Token);
            }
        }
        catch (OperationCanceledException) when (cts.Token.IsCancellationRequested)
        {
            Console.WriteLine("搜索操作被取消");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"搜索过程中发生异常: {ex.Message}");
        }
        
        Console.WriteLine($"最终找到 {videos.Count} 个GPU相关视频");
        return videos;
    }
    
    // 演示模式：生成模拟的GPU相关视频数据
    static List<YouTubeVideo> GetDemoYouTubeVideos()
    {
        var demoVideos = new List<YouTubeVideo>
        {
            new YouTubeVideo
            {
                Title = "GPU Programming Tutorial for Beginners",
                VideoUrl = "https://www.youtube.com/watch?v=demo1",
                ChannelName = "Tech Tutorials",
                LikeCount = 2500,
                PublishedAt = DateTime.Now.AddMonths(-6),
                Description = "Learn the basics of GPU programming with practical examples"
            },
            new YouTubeVideo
            {
                Title = "CUDA Programming Masterclass",
                VideoUrl = "https://www.youtube.com/watch?v=demo2",
                ChannelName = "AI Developers",
                LikeCount = 1800,
                PublishedAt = DateTime.Now.AddMonths(-3),
                Description = "Complete guide to CUDA programming for GPU acceleration"
            },
            new YouTubeVideo
            {
                Title = "显卡性能优化指南",
                VideoUrl = "https://www.youtube.com/watch?v=demo3",
                ChannelName = "硬件评测",
                LikeCount = 3200,
                PublishedAt = DateTime.Now.AddMonths(-1),
                Description = "如何优化显卡性能以获得更好的游戏体验"
            },
            new YouTubeVideo
            {
                Title = "GPU vs CPU: What's the Difference?",
                VideoUrl = "https://www.youtube.com/watch?v=demo4",
                ChannelName = "Computer Science",
                LikeCount = 4200,
                PublishedAt = DateTime.Now.AddMonths(-12),
                Description = "Understanding the fundamental differences between GPU and CPU architecture"
            },
            new YouTubeVideo
            {
                Title = "深度学习中的GPU加速技术",
                VideoUrl = "https://www.youtube.com/watch?v=demo5",
                ChannelName = "AI研究",
                LikeCount = 1500,
                PublishedAt = DateTime.Now.AddMonths(-8),
                Description = "探讨GPU在深度学习中的重要作用和优化技巧"
            }
        };
        
        Console.WriteLine($"🎯 生成 {demoVideos.Count} 条模拟GPU视频数据");
        foreach (var video in demoVideos)
        {
            Console.WriteLine($"📹 {video.Title} (点赞: {video.LikeCount})");
        }
        
        return demoVideos;
    }
    
    // 解析YouTube视频数据的方法
    static YouTubeVideo ParseYouTubeVideo(JsonElement item)
    {
        try
        {
            // 获取视频基本信息
            var snippet = item.GetProperty("snippet");
            
            string title = snippet.GetProperty("title").GetString() ?? "";
            string description = snippet.GetProperty("description").GetString() ?? "";
            string channelName = snippet.GetProperty("channelTitle").GetString() ?? "";
            
            // 解析发布时间
            DateTime publishedAt = DateTime.Parse(snippet.GetProperty("publishedAt").GetString());
            
            // 获取视频ID
            string videoId = "";
            if (item.TryGetProperty("id", out var idElement))
            {
                if (idElement.ValueKind == JsonValueKind.Object)
                {
                    if (idElement.TryGetProperty("videoId", out var videoIdElement))
                    {
                        videoId = videoIdElement.GetString() ?? "";
                    }
                }
                else if (idElement.ValueKind == JsonValueKind.String)
                {
                    videoId = idElement.GetString() ?? "";
                }
            }
            
            if (string.IsNullOrEmpty(videoId))
            {
                Console.WriteLine($"⚠️  无法获取视频ID，跳过视频: {title}");
                return null;
            }
            
            // 创建视频对象
            var video = new YouTubeVideo
            {
                Title = title,
                VideoUrl = $"https://www.youtube.com/watch?v={videoId}",
                ChannelName = channelName,
                LikeCount = 0, // 搜索API不包含点赞数，需要后续获取
                PublishedAt = publishedAt,
                Description = description
            };
            
            return video;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ 解析视频数据时出错: {ex.Message}");
            return null;
        }
    }
    
    // 获取YouTube API密钥的方法
    static string GetYouTubeApiKey()
    {
        // 优先从环境变量获取
        string apiKey = Environment.GetEnvironmentVariable("YOUTUBE_API_KEY");
        
        if (!string.IsNullOrEmpty(apiKey))
        {
            Console.WriteLine("✅ 使用环境变量中的API密钥");
            return apiKey;
        }
        
        // 使用用户提供的真实API密钥
        string realApiKey = "AIzaSyCV0NXV4xZE8cq4miFkv-_J5BKeoj6t3r8";
        
        // 检查密钥是否有效（不是默认值或空值）
        if (!string.IsNullOrEmpty(realApiKey) && realApiKey.Length > 20)
        {
            Console.WriteLine("✅ 使用真实API密钥进行YouTube数据抓取");
            return realApiKey;
        }
        
        Console.WriteLine("⚠️  警告：未设置有效的API密钥，将使用模拟数据进行演示");
        return "DEMO_MODE"; // 返回特殊标记表示使用模拟模式
    }

    
    static async Task ExportToCsv(List<YouTubeVideo> videos, string filename)
    {
        using var writer = new StreamWriter(filename, false, System.Text.Encoding.UTF8);
        
        // 写入CSV头部（添加BOM以确保Excel正确识别UTF-8编码）
        writer.Write('\uFEFF'); // UTF-8 BOM
        await writer.WriteLineAsync("视频标题,视频网址,频道名称,点赞数,发布时间,视频简介");
        
        // 写入数据
        foreach (var video in videos)
        {
            // 处理CSV特殊字符和长文本
            string description = video.Description ?? "";
            string title = video.Title ?? "";
            
            // 清理文本：移除所有控制字符和不可打印字符
            description = new string(description.Where(c => !char.IsControl(c)).ToArray());
            title = new string(title.Where(c => !char.IsControl(c)).ToArray());
            
            // 清理文本：移除换行符和制表符
            description = description.Replace("\r\n", " ").Replace("\n", " ").Replace("\t", " ");
            title = title.Replace("\r\n", " ").Replace("\n", " ").Replace("\t", " ");
            
            // 限制描述长度，避免CSV文件过大
            if (description.Length > 200)
            {
                description = description.Substring(0, 200) + "...";
            }
            
            // 处理CSV特殊字符 - 用引号包裹文本字段
            description = description.Replace("\"", "\"\"");
            description = $"\"{description}\"";
            
            title = title.Replace("\"", "\"\"");
            title = $"\"{title}\"";
            
            string channelName = video.ChannelName ?? "";
            if (channelName.Contains(",") || channelName.Contains("\"") || channelName.Contains("\n") || channelName.Contains("\r"))
            {
                channelName = channelName.Replace("\"", "\"\"");
                channelName = $"\"{channelName}\"";
            }
            
            await writer.WriteLineAsync($"{title},{video.VideoUrl},{channelName},{video.LikeCount},{video.PublishedAt:yyyy-MM-dd HH:mm:ss},{description}");
        }
    }
}