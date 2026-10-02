using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;

namespace Spider
{
    public class BilibiliVideo
    {
        [JsonPropertyName("bvid")]
        public string Bvid { get; set; } = string.Empty;
        
        [JsonPropertyName("title")]
        public string Title { get; set; } = string.Empty;
        
        [JsonPropertyName("description")]
        public string Description { get; set; } = string.Empty;
        
        [JsonPropertyName("owner")]
        public VideoOwner Owner { get; set; } = new VideoOwner();
        
        [JsonPropertyName("stat")]
        public VideoStat Stat { get; set; } = new VideoStat();
        
        [JsonPropertyName("pubdate")]
        public long PubDate { get; set; }
        
        public string VideoUrl => $"https://www.bilibili.com/video/{Bvid}";
        
        public string AuthorName => Owner?.Name ?? "未知作者";
        
        public int LikeCount => Stat?.Like ?? 0;
        
        public DateTime PublishDate => DateTimeOffset.FromUnixTimeSeconds(PubDate).DateTime;
    }
    
    public class VideoOwner
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;
    }
    
    public class VideoStat
    {
        [JsonPropertyName("like")]
        public int Like { get; set; }
    }
    
    public class BilibiliSearchResponse
    {
        [JsonPropertyName("code")]
        public int Code { get; set; }
        
        [JsonPropertyName("data")]
        public SearchData Data { get; set; } = new SearchData();
        
        [JsonPropertyName("message")]
        public string Message { get; set; } = string.Empty;
    }
    
    public class SearchData
    {
        [JsonPropertyName("result")]
        public List<BilibiliVideo> Result { get; set; } = new List<BilibiliVideo>();
        
        [JsonPropertyName("numPages")]
        public int NumPages { get; set; }
        
        [JsonPropertyName("numResults")]
        public int NumResults { get; set; }
    }

    public class BilibiliSpider
    {
        private static readonly HttpClient httpClient = new HttpClient();
        
        public static async Task RunAsync()
        {
            Console.WriteLine("哔哩哔哩视频爬虫程序启动...");
            
            // 配置参数
            string keyword = "GPU";
            int minLikes = 1000;
            int maxResults = 1000;
            int maxYears = 3;
            TimeSpan timeout = TimeSpan.FromMinutes(5);
            
            try
            {
                // 设置HTTP客户端超时
                httpClient.Timeout = timeout;
                
                // 设置User-Agent模拟浏览器访问
                httpClient.DefaultRequestHeaders.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
                
                var videos = await SearchBilibiliVideos(keyword, minLikes, maxYears, maxResults, timeout);
                
                if (videos.Count > 0)
                {
                    // 生成带时间戳的文件名
                    string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                    string csvFilename = $"bilibili_videos_{timestamp}.csv";
                    
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
            
            Console.WriteLine("哔哩哔哩爬虫程序执行完毕");
        }

        private static async Task<List<BilibiliVideo>> SearchBilibiliVideos(string keyword, int minLikes, int maxYears, int maxResults, TimeSpan timeout)
        {
            var videos = new List<BilibiliVideo>();
            int page = 1;
            const int perPage = 20; // B站搜索每页20条
            
            // 计算3年前的日期
            DateTime threeYearsAgo = DateTime.Now.AddYears(-maxYears);
            long threeYearsAgoTimestamp = new DateTimeOffset(threeYearsAgo).ToUnixTimeSeconds();
            
            using var cts = new CancellationTokenSource(timeout);
            
            while (videos.Count < maxResults)
            {
                try
                {
                    // 构建B站搜索URL
                    string url = $"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={Uri.EscapeDataString(keyword)}&page={page}&page_size={perPage}";
                    
                    Console.WriteLine($"正在搜索第{page}页... URL: {url}");
                    
                    var response = await httpClient.GetAsync(url, cts.Token);
                    
                    if (!response.IsSuccessStatusCode)
                    {
                        Console.WriteLine($"HTTP错误: {response.StatusCode} - {response.ReasonPhrase}");
                        var errorContent = await response.Content.ReadAsStringAsync(cts.Token);
                        Console.WriteLine($"错误详情: {errorContent}");
                        break;
                    }
                    
                    var json = await response.Content.ReadAsStringAsync(cts.Token);
                    Console.WriteLine($"API响应JSON长度: {json.Length} 字符");
                    
                    try
                    {
                        var options = new JsonSerializerOptions
                        {
                            PropertyNameCaseInsensitive = true
                        };
                        var searchResponse = JsonSerializer.Deserialize<BilibiliSearchResponse>(json, options);
                        
                        if (searchResponse == null || searchResponse.Code != 0)
                        {
                            Console.WriteLine($"API返回错误: {searchResponse?.Message ?? "未知错误"}");
                            break;
                        }
                        
                        if (searchResponse.Data?.Result == null || searchResponse.Data.Result.Count == 0)
                        {
                            Console.WriteLine($"没有找到视频，搜索结束");
                            break;
                        }
                        
                        Console.WriteLine($"本页找到 {searchResponse.Data.Result.Count} 个视频，总共 {searchResponse.Data.NumResults} 个结果");
                        
                        // 过滤符合条件的视频
                        foreach (var video in searchResponse.Data.Result)
                        {
                            // 检查点赞数和发布时间
                            if (video.LikeCount >= minLikes && video.PublishDate >= threeYearsAgo)
                            {
                                videos.Add(video);
                                Console.WriteLine($"找到视频: {video.Title} (点赞: {video.LikeCount}, 作者: {video.AuthorName})");
                                
                                if (videos.Count >= maxResults)
                                {
                                    Console.WriteLine("已达到最大抓取数量限制");
                                    break;
                                }
                            }
                        }
                        
                        page++;
                        
                        // B站API限制：短暂延迟避免速率限制
                        await Task.Delay(1000, cts.Token);
                    }
                    catch (JsonException ex)
                    {
                        Console.WriteLine($"JSON反序列化错误: {ex.Message}");
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
            
            return videos;
        }

        private static async Task ExportToCsv(List<BilibiliVideo> videos, string filename)
        {
            using var writer = new StreamWriter(filename, false, System.Text.Encoding.UTF8);
            
            // 写入CSV头部（添加BOM以确保Excel正确识别UTF-8编码）
            writer.Write('\uFEFF'); // UTF-8 BOM
            await writer.WriteLineAsync("视频标题,视频网址,作者名字,点赞数量,发布时间,视频简介");
            
            // 写入数据
            foreach (var video in videos)
            {
                // 处理CSV特殊字符和长文本
                string title = video.Title ?? "";
                string description = video.Description ?? "";
                string author = video.AuthorName ?? "";
                
                // 清理文本：移除所有控制字符和不可打印字符
                title = new string(title.Where(c => !char.IsControl(c)).ToArray());
                description = new string(description.Where(c => !char.IsControl(c)).ToArray());
                author = new string(author.Where(c => !char.IsControl(c)).ToArray());
                
                // 清理文本：移除换行符和制表符
                title = title.Replace("\r\n", " ").Replace("\n", " ").Replace("\t", " ");
                description = description.Replace("\r\n", " ").Replace("\n", " ").Replace("\t", " ");
                author = author.Replace("\r\n", " ").Replace("\n", " ").Replace("\t", " ");
                
                // 限制描述长度，避免CSV文件过大
                if (description.Length > 200)
                {
                    description = description.Substring(0, 200) + "...";
                }
                
                // 处理CSV特殊字符 - 用引号包裹文本字段
                title = title.Replace("\"", "\"\"");
                title = $"\"{title}\"";
                
                description = description.Replace("\"", "\"\"");
                description = $"\"{description}\"";
                
                author = author.Replace("\"", "\"\"");
                author = $"\"{author}\"";
                
                string publishDate = video.PublishDate.ToString("yyyy-MM-dd HH:mm:ss");
                
                await writer.WriteLineAsync($"{title},{video.VideoUrl},{author},{video.LikeCount},{publishDate},{description}");
            }
        }
    }
}