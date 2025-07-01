#!/usr/bin/env python3
"""
Basic Memory Daily Traction Report - Clean Version
Automated tracking across GitHub, Discord, YouTube, and Reddit
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
        self.discord_bot_token = os.getenv('DISCORD_BOT_TOKEN')
        self.discord_server_id = os.getenv('DISCORD_SERVER_ID')
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        
        # Reddit setup
        self.reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_SECRET'),
            user_agent='BasicMemoryTracker:v2.0'
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
            return ""  # Don't show change on first run
        elif direction == "📈":
            return f"(+{change})"
        elif direction == "📉":
            return f"(-{change})"
        else:
            return ""  # Don't show (±0)

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
            
            return {
                'stars': repo_data.get('stargazers_count', 0),
                'forks': repo_data.get('forks_count', 0),
                'traffic_unique': traffic_data.get('uniques', 0) if traffic_data.get('uniques', 0) > 0 else None
            }
        except Exception as e:
            print(f"GitHub API error: {e}")
            return {'error': str(e)}

    def get_discord_metrics(self):
        """Get Discord server metrics using multiple approaches"""
        try:
            headers = {'Authorization': f'Bot {self.discord_bot_token}'}
            
            # Try method 1: Get guild info with approximate member count
            guild_url = f'https://discord.com/api/v10/guilds/{self.discord_server_id}?with_counts=true'
            response = requests.get(guild_url, headers=headers)
            
            if response.status_code == 200:
                guild_data = response.json()
                # Try multiple fields that might contain member count
                member_count = (
                    guild_data.get('approximate_member_count') or 
                    guild_data.get('member_count') or 
                    guild_data.get('members')
                )
                
                if member_count:
                    return {'members': member_count}
            
            # Method 2: Try to get members list (if bot has permission)
            members_url = f'https://discord.com/api/v10/guilds/{self.discord_server_id}/members?limit=1000'
            members_response = requests.get(members_url, headers=headers)
            
            if members_response.status_code == 200:
                members_data = members_response.json()
                return {'members': len(members_data)}
            
            # Method 3: Fallback - return 0 but note the issue
            print(f"⚠️ Discord API responses: Guild: {response.status_code}, Members: {members_response.status_code}")
            return {'members': 0}
                
        except Exception as e:
            print(f"Discord API error: {e}")
            return {'members': 0}

    def get_reddit_metrics(self):
        """Get Reddit metrics for r/BasicMemory only"""
        try:
            metrics = {
                'subreddit_members': 0
            }
            
            # Check r/BasicMemory if it exists
            try:
                basic_memory_sub = self.reddit.subreddit('BasicMemory')
                metrics['subreddit_members'] = basic_memory_sub.subscribers
            except Exception as e:
                print(f"r/BasicMemory not found or error: {e}")
                metrics['subreddit_members'] = 0
                
            return metrics
        except Exception as e:
            print(f"Reddit API error: {e}")
            return {'subreddit_members': 0}

    def get_youtube_metrics(self):
        """Get YouTube channel metrics"""
        try:
            # Try to find channel by handle first
            search_response = self.youtube.search().list(
                part='snippet',
                q='basicmachines-co',
                type='channel',
                maxResults=5
            ).execute()
            
            channel_id = None
            if search_response.get('items'):
                # Look for exact match or best match
                for item in search_response['items']:
                    channel_title = item['snippet']['title'].lower()
                    if 'basic' in channel_title and 'machine' in channel_title:
                        channel_id = item['snippet']['channelId']
                        break
                
                # If no exact match, use first result
                if not channel_id and search_response['items']:
                    channel_id = search_response['items'][0]['snippet']['channelId']
            
            if channel_id:
                # Get channel statistics
                channel_response = self.youtube.channels().list(
                    part='statistics,snippet',
                    id=channel_id
                ).execute()
                
                if channel_response.get('items'):
                    stats = channel_response['items'][0]['statistics']
                    return {
                        'subscribers': int(stats.get('subscriberCount', 0)),
                        'total_views': int(stats.get('viewCount', 0)),
                        'video_count': int(stats.get('videoCount', 0))
                    }
            
            # Fallback: return placeholder data
            print("⚠️ YouTube channel not found, using placeholder data")
            return {
                'subscribers': 0,
                'total_views': 0,
                'video_count': 0
            }
                
        except Exception as e:
            print(f"YouTube API error: {e}")
            return {
                'subscribers': 0,
                'total_views': 0,
                'video_count': 0
            }

    def create_discord_embed(self, current_metrics, previous_metrics):
        """Create clean Discord embed with all metrics and growth indicators"""
        
        github_data = current_metrics.get('github', {})
        discord_data = current_metrics.get('discord', {})
        reddit_data = current_metrics.get('reddit', {})
        youtube_data = current_metrics.get('youtube', {})
        
        prev_github = previous_metrics.get('github', {})
        prev_discord = previous_metrics.get('discord', {})
        prev_reddit = previous_metrics.get('reddit', {})
        prev_youtube = previous_metrics.get('youtube', {})
        
        # Calculate changes
        star_change, star_dir = self.calculate_change(github_data.get('stars', 0), prev_github, 'stars')
        discord_change, discord_dir = self.calculate_change(discord_data.get('members', 0), prev_discord, 'members')
        reddit_change, reddit_dir = self.calculate_change(reddit_data.get('subreddit_members', 0), prev_reddit, 'subreddit_members')
        sub_change, sub_dir = self.calculate_change(youtube_data.get('subscribers', 0), prev_youtube, 'subscribers')
        view_change, view_dir = self.calculate_change(youtube_data.get('total_views', 0), prev_youtube, 'total_views')
        
        # Traffic display logic
        traffic_display = "Data pending" if github_data.get('traffic_unique') is None else f"{github_data.get('traffic_unique', 0)} visitors"
        
        embed = {
            "title": "🚀 Basic Memory Daily Traction Report",
            "description": f"📅 {datetime.now().strftime('%A, %B %d, %Y')}",
            "color": 0x00ff88,
            "fields": [
                {
                    "name": "⭐ GitHub",
                    "value": f"""
**Stars:** {github_data.get('stars', 'N/A')} {self.format_change(star_change, star_dir)}
**Forks:** {github_data.get('forks', 'N/A')}
**Traffic:** {traffic_display}
                    """.strip(),
                    "inline": True
                },
                {
                    "name": "💬 Community", 
                    "value": f"""
**Discord:** {discord_data.get('members', 'N/A')} members {self.format_change(discord_change, discord_dir)}
**r/BasicMemory:** {reddit_data.get('subreddit_members', 'N/A')} {self.format_change(reddit_change, reddit_dir)}

                    """.strip(),
                    "inline": True
                },
                {
                    "name": "📺 YouTube",
                    "value": f"""
**Subscribers:** {youtube_data.get('subscribers', 'N/A')} {self.format_change(sub_change, sub_dir)}
**Views:** {youtube_data.get('total_views', 'N/A')} {self.format_change(view_change, view_dir)}
**Videos:** {youtube_data.get('video_count', 'N/A')}
                    """.strip(),
                    "inline": True
                }
            ],
            "footer": {
                "text": f"🤖 Automated by Basic Memory"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Add daily highlight if there's significant growth
        highlights = []
        if discord_change > 5:
            highlights.append(f"Discord gained {discord_change} new members!")
        if star_change > 10:
            highlights.append(f"GitHub stars up {star_change}!")
        if sub_change > 0:
            highlights.append(f"YouTube gained {sub_change} subscribers!")
            
        if highlights:
            embed["fields"].append({
                "name": "📈 Today's Highlight",
                "value": highlights[0],  # Show the first/most important highlight
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
        
        print("💬 Collecting Discord metrics...")
        discord_data = self.get_discord_metrics()
        
        print("🗨️ Collecting Reddit metrics...")
        reddit_data = self.get_reddit_metrics()
        
        print("📺 Collecting YouTube metrics...")
        youtube_data = self.get_youtube_metrics()
        
        # Combine current metrics
        current_metrics = {
            'github': github_data,
            'discord': discord_data,
            'reddit': reddit_data,
            'youtube': youtube_data
        }
        
        # Create and send report
        print("🎨 Creating clean Discord embed...")
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
💬 Discord Members: {discord_data.get('members', 'Error')}
🗨️ r/BasicMemory: {reddit_data.get('subreddit_members', 'Error')} 
📺 YouTube Subscribers: {youtube_data.get('subscribers', 'Error')}
        """)

if __name__ == "__main__":
    tracker = BasicMemoryTracker()
    tracker.run_daily_report()
