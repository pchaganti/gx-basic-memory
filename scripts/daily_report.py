#!/usr/bin/env python3
"""
Basic Memory Daily Traction Report - Enhanced with Growth Tracking
Automated tracking across GitHub, Reddit, YouTube with daily change indicators
"""

import os
import requests
import json
from datetime import datetime, timedelta
import praw
from googleapiclient.discovery import build
from dateutil import parser
import base64

class BasicMemoryTracker:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK')
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        
        # Reddit setup
        self.reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_SECRET'),
            user_agent='BasicMemoryTracker:v1.0'
        )
        
        # YouTube setup
        self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
        
        self.repo_owner = 'basicmachines-co'
        self.repo_name = 'basic-memory'
        self.youtube_channel = 'basicmachines-co'
        self.metrics_file = 'data/daily_metrics.json'

    def get_previous_metrics(self):
        """Get yesterday's metrics from GitHub repo storage"""
        try:
            headers = {'Authorization': f'token {self.github_token}'}
            url = f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/{self.metrics_file}'
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                file_data = response.json()
                content = base64.b64decode(file_data['content']).decode('utf-8')
                return json.loads(content)
            else:
                print("📝 No previous metrics found - this is the first run!")
                return {}
        except Exception as e:
            print(f"⚠️ Could not load previous metrics: {e}")
            return {}

    def save_current_metrics(self, metrics):
        """Save today's metrics to GitHub repo for tomorrow's comparison"""
        try:
            headers = {'Authorization': f'token {self.github_token}'}
            
            # Prepare data
            metrics_data = {
                'date': datetime.now().isoformat(),
                'metrics': metrics
            }
            content = json.dumps(metrics_data, indent=2)
            encoded_content = base64.b64encode(content.encode()).decode()
            
            # Check if file exists
            file_url = f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/{self.metrics_file}'
            existing_response = requests.get(file_url, headers=headers)
            
            payload = {
                'message': f'📊 Daily metrics update - {datetime.now().strftime("%Y-%m-%d")}',
                'content': encoded_content
            }
            
            if existing_response.status_code == 200:
                # File exists, update it
                payload['sha'] = existing_response.json()['sha']
                response = requests.put(file_url, headers=headers, json=payload)
            else:
                # File doesn't exist, create it
                response = requests.put(file_url, headers=headers, json=payload)
            
            if response.status_code in [200, 201]:
                print("✅ Metrics saved for tomorrow's comparison!")
            else:
                print(f"⚠️ Failed to save metrics: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ Error saving metrics: {e}")

    def calculate_change(self, current, previous, key):
        """Calculate the change between current and previous values"""
        if not previous or key not in previous:
            return 0, "🆕"
        
        change = current - previous[key]
        if change > 0:
            return change, "📈"
        elif change < 0:
            return abs(change), "📉"
        else:
            return 0, "➡️"

    def format_change(self, change, direction):
        """Format the change indicator for display"""
        if direction == "🆕":
            return "🆕"
        elif direction == "📈":
            return f"(+{change})"
        elif direction == "📉":
            return f"(-{change})"
        else:
            return "(±0)"

    def get_github_metrics(self):
        """Get GitHub repository metrics"""
        try:
            headers = {'Authorization': f'token {self.github_token}'}
            
            # Repository stats
            repo_url = f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}'
            repo_response = requests.get(repo_url, headers=headers)
            repo_data = repo_response.json()
            
            # Traffic stats (requires push access)
            traffic_url = f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/traffic/views'
            traffic_response = requests.get(traffic_url, headers=headers)
            traffic_data = traffic_response.json() if traffic_response.status_code == 200 else {}
            
            # Recent issues
            issues_url = f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/issues'
            issues_response = requests.get(issues_url, headers=headers)
            issues_data = issues_response.json() if issues_response.status_code == 200 else []
            
            return {
                'stars': repo_data.get('stargazers_count', 0),
                'forks': repo_data.get('forks_count', 0),
                'watchers': repo_data.get('watchers_count', 0),
                'open_issues': repo_data.get('open_issues_count', 0),
                'traffic_views': traffic_data.get('count', 0),
                'traffic_unique': traffic_data.get('uniques', 0),
                'recent_issues': len([i for i in issues_data if 
                    parser.parse(i['created_at']).date() >= (datetime.now() - timedelta(days=1)).date()])
            }
        except Exception as e:
            print(f"GitHub API error: {e}")
            return {'error': str(e)}

    def get_reddit_metrics(self):
        """Get Reddit metrics for Basic Memory mentions"""
        try:
            metrics = {
                'total_mentions': 0,
                'subreddit_members': 0,
                'top_posts': [],
                'hot_discussions': []
            }
            
            # Search for Basic Memory mentions
            search_results = list(self.reddit.subreddit('all').search(
                'Basic Memory', time_filter='day', limit=25
            ))
            metrics['total_mentions'] = len(search_results)
            
            # Get top posts
            for post in search_results[:3]:
                metrics['top_posts'].append({
                    'title': post.title[:50] + '...' if len(post.title) > 50 else post.title,
                    'score': post.score,
                    'subreddit': post.subreddit.display_name,
                    'num_comments': post.num_comments
                })
            
            # Check r/BasicMemory if it exists
            try:
                basic_memory_sub = self.reddit.subreddit('BasicMemory')
                metrics['subreddit_members'] = basic_memory_sub.subscribers
            except:
                metrics['subreddit_members'] = 0
                
            return metrics
        except Exception as e:
            print(f"Reddit API error: {e}")
            return {'error': str(e)}

    def get_youtube_metrics(self):
        """Get YouTube channel metrics"""
        try:
            # Get channel statistics
            channel_response = self.youtube.channels().list(
                part='statistics,snippet',
                forUsername=self.youtube_channel
            ).execute()
            
            if not channel_response['items']:
                # Try by channel handle
                search_response = self.youtube.search().list(
                    part='snippet',
                    q=f'@{self.youtube_channel}',
                    type='channel',
                    maxResults=1
                ).execute()
                
                if search_response['items']:
                    channel_id = search_response['items'][0]['snippet']['channelId']
                    channel_response = self.youtube.channels().list(
                        part='statistics,snippet',
                        id=channel_id
                    ).execute()
            
            if channel_response['items']:
                stats = channel_response['items'][0]['statistics']
                return {
                    'subscribers': int(stats.get('subscriberCount', 0)),
                    'total_views': int(stats.get('viewCount', 0)),
                    'video_count': int(stats.get('videoCount', 0))
                }
            else:
                return {'error': 'Channel not found'}
                
        except Exception as e:
            print(f"YouTube API error: {e}")
            return {'error': str(e)}

    def create_discord_embed(self, current_metrics, previous_metrics):
        """Create beautiful Discord embed with all metrics and growth indicators"""
        
        github_data = current_metrics.get('github', {})
        reddit_data = current_metrics.get('reddit', {})
        youtube_data = current_metrics.get('youtube', {})
        
        prev_github = previous_metrics.get('github', {})
        prev_reddit = previous_metrics.get('reddit', {})
        prev_youtube = previous_metrics.get('youtube', {})
        
        # Calculate changes
        star_change, star_dir = self.calculate_change(github_data.get('stars', 0), prev_github, 'stars')
        sub_change, sub_dir = self.calculate_change(youtube_data.get('subscribers', 0), prev_youtube, 'subscribers')
        view_change, view_dir = self.calculate_change(youtube_data.get('total_views', 0), prev_youtube, 'total_views')
        reddit_change, reddit_dir = self.calculate_change(reddit_data.get('total_mentions', 0), prev_reddit, 'total_mentions')
        member_change, member_dir = self.calculate_change(reddit_data.get('subreddit_members', 0), prev_reddit, 'subreddit_members')
        
        # Calculate total reach
        total_reach = (
            github_data.get('traffic_unique', 0) + 
            reddit_data.get('total_mentions', 0) * 100 +
            youtube_data.get('total_views', 0)
        )
        
        embed = {
            "title": "🚀 Basic Memory Daily Traction Report",
            "description": f"📅 {datetime.now().strftime('%A, %B %d, %Y')}",
            "color": 0x00ff88,
            "fields": [
                {
                    "name": "⭐ GitHub Metrics",
                    "value": f"""
**Stars:** {github_data.get('stars', 'N/A')} {star_dir} {self.format_change(star_change, star_dir)}
**Forks:** {github_data.get('forks', 'N/A')} 🍴
**Traffic:** {github_data.get('traffic_unique', 'N/A')} unique visitors 👀
**Issues:** {github_data.get('recent_issues', 0)} new today 🐛
                    """.strip(),
                    "inline": True
                },
                {
                    "name": "🗨️ Reddit Activity", 
                    "value": f"""
**Mentions:** {reddit_data.get('total_mentions', 'N/A')} {reddit_dir} {self.format_change(reddit_change, reddit_dir)}
**r/BasicMemory:** {reddit_data.get('subreddit_members', 'N/A')} {member_dir} {self.format_change(member_change, member_dir)}
**Hot Posts:** {len(reddit_data.get('top_posts', []))} trending 🔥
                    """.strip(),
                    "inline": True
                },
                {
                    "name": "📺 YouTube Stats",
                    "value": f"""
**Subscribers:** {youtube_data.get('subscribers', 'N/A')} {sub_dir} {self.format_change(sub_change, sub_dir)}
**Total Views:** {youtube_data.get('total_views', 'N/A'):,} {view_dir} {self.format_change(view_change, view_dir)}
**Videos:** {youtube_data.get('video_count', 'N/A')} 🎬
                    """.strip(),
                    "inline": True
                }
            ],
            "footer": {
                "text": f"🤖 Automated by Basic Memory • Daily Reach: {total_reach:,}"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Add top Reddit posts if available
        if reddit_data.get('top_posts'):
            top_post = reddit_data['top_posts'][0]
            embed["fields"].append({
                "name": "🔥 Top Reddit Post",
                "value": f"**{top_post['title']}**\n📊 {top_post['score']} upvotes • 💬 {top_post['num_comments']} comments\n📍 r/{top_post['subreddit']}",
                "inline": False
            })
        
        return embed

    def send_discord_report(self, embed):
        """Send the report to Discord"""
        try:
            payload = {"embeds": [embed]}
            response = requests.post(self.discord_webhook, json=payload)
            
            if response.status_code == 204:
                print("✅ Discord report sent successfully!")
                return True
            else:
                print(f"❌ Discord webhook failed: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"Discord send error: {e}")
            return False

    def run_daily_report(self):
        """Main function to generate and send daily report"""
        print("🚀 Starting Basic Memory Daily Traction Report...")
        
        # Load previous metrics
        print("📊 Loading previous metrics...")
        previous_metrics = self.get_previous_metrics()
        
        # Collect current metrics
        print("📊 Collecting GitHub metrics...")
        github_data = self.get_github_metrics()
        
        print("🗨️ Collecting Reddit metrics...")
        reddit_data = self.get_reddit_metrics()
        
        print("📺 Collecting YouTube metrics...")
        youtube_data = self.get_youtube_metrics()
        
        # Combine current metrics
        current_metrics = {
            'github': github_data,
            'reddit': reddit_data,
            'youtube': youtube_data
        }
        
        # Create and send report
        print("🎨 Creating Discord embed with growth tracking...")
        embed = self.create_discord_embed(current_metrics, previous_metrics.get('metrics', {}))
        
        print("📤 Sending to Discord...")
        success = self.send_discord_report(embed)
        
        # Save current metrics for tomorrow
        print("💾 Saving metrics for tomorrow's comparison...")
        self.save_current_metrics(current_metrics)
        
        if success:
            print("🎉 Daily traction report completed successfully!")
        else:
            print("😞 Report failed to send")
            
        # Print summary for GitHub Actions logs
        print(f"""
📊 DAILY SUMMARY:
⭐ GitHub Stars: {github_data.get('stars', 'Error')}
👥 Reddit Mentions: {reddit_data.get('total_mentions', 'Error')} 
📺 YouTube Subscribers: {youtube_data.get('subscribers', 'Error')}
📺 YouTube Views: {youtube_data.get('total_views', 'Error')}
        """)

if __name__ == "__main__":
    tracker = BasicMemoryTracker()
    tracker.run_daily_report()
