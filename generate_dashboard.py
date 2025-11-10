#!/usr/bin/env python3
import os
from github import Github
from datetime import datetime

# Initialize GitHub client
g = Github(os.environ['GITHUB_TOKEN'])
user_login = os.environ.get('DASHBOARD_USER', 'linservbot')

# Get user or organization
try:
    # Try as organization first
    entity = g.get_organization(user_login)
    print(f"Fetching workflow status for organization: {user_login}")
except:
    # Fall back to user
    entity = g.get_user(user_login)
    print(f"Fetching workflow status for user: {user_login}")

# Get all repos
repos = entity.get_repos()

dashboard_data = []

for repo in repos:
    try:
        # Skip archived repos
        if repo.archived:
            continue
            
        # Get workflow runs
        workflows = repo.get_workflows()
        
        if workflows.totalCount == 0:
            continue
            
        # Get latest run for each workflow
        runs = repo.get_workflow_runs()
        
        if runs.totalCount == 0:
            continue
            
        latest_run = runs[0]
        
        repo_data = {
            'name': repo.full_name,
            'url': repo.html_url,
            'workflow_name': latest_run.name,
            'status': latest_run.status,
            'conclusion': latest_run.conclusion,
            'run_url': latest_run.html_url,
            'updated_at': latest_run.updated_at.isoformat(),
            'branch': latest_run.head_branch
        }
        
        dashboard_data.append(repo_data)
        print(f"  ✓ {repo.full_name}: {latest_run.conclusion or latest_run.status}")
        
    except Exception as e:
        print(f"  ✗ Error fetching {repo.full_name}: {e}")
        continue

# Sort by status (failed first, then in progress, then success)
status_priority = {'failure': 0, 'cancelled': 1, 'in_progress': 2, 'success': 3, 'completed': 4}
dashboard_data.sort(key=lambda x: status_priority.get(x['conclusion'] or x['status'], 99))

# Generate HTML
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Actions Dashboard - {user_login}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            margin-bottom: 10px;
            color: #58a6ff;
        }}
        .last-updated {{
            color: #8b949e;
            margin-bottom: 30px;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        .stat-card {{
            background: #161b22;
            padding: 20px;
            border-radius: 6px;
            border: 1px solid #30363d;
            flex: 1;
            min-width: 150px;
        }}
        .stat-number {{
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #8b949e;
            font-size: 14px;
        }}
        .success {{ color: #3fb950; }}
        .failure {{ color: #f85149; }}
        .in-progress {{ color: #d29922; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #161b22;
            border-radius: 6px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #30363d;
        }}
        th {{
            background: #0d1117;
            font-weight: 600;
            color: #8b949e;
            text-transform: uppercase;
            font-size: 12px;
        }}
        tr:hover {{
            background: #1c2128;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-success {{
            background: #1a3c25;
            color: #3fb950;
        }}
        .badge-failure {{
            background: #3c1c1f;
            color: #f85149;
        }}
        .badge-in-progress {{
            background: #3c2e1a;
            color: #d29922;
        }}
        .badge-cancelled {{
            background: #2b2f36;
            color: #8b949e;
        }}
        a {{
            color: #58a6ff;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .repo-name {{
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 GitHub Actions Dashboard - {user_login}</h1>
        <p class="last-updated">Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{len(dashboard_data)}</div>
                <div class="stat-label">Total Repos</div>
            </div>
            <div class="stat-card">
                <div class="stat-number success">{sum(1 for r in dashboard_data if r['conclusion'] == 'success')}</div>
                <div class="stat-label">Passing</div>
            </div>
            <div class="stat-card">
                <div class="stat-number failure">{sum(1 for r in dashboard_data if r['conclusion'] == 'failure')}</div>
                <div class="stat-label">Failing</div>
            </div>
            <div class="stat-card">
                <div class="stat-number in-progress">{sum(1 for r in dashboard_data if r['status'] == 'in_progress')}</div>
                <div class="stat-label">In Progress</div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Repository</th>
                    <th>Workflow</th>
                    <th>Branch</th>
                    <th>Status</th>
                    <th>Last Updated</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
"""

for repo in dashboard_data:
    conclusion = repo['conclusion'] or repo['status']
    badge_class = f"badge-{conclusion.replace('_', '-')}" if conclusion else "badge-cancelled"
    
    # Format date
    try:
        updated = datetime.fromisoformat(repo['updated_at'].replace('Z', '+00:00'))
        time_str = updated.strftime('%Y-%m-%d %H:%M')
    except:
        time_str = repo['updated_at']
    
    html += f"""
                <tr>
                    <td class="repo-name"><a href="{repo['url']}" target="_blank">{repo['name']}</a></td>
                    <td>{repo['workflow_name']}</td>
                    <td>{repo['branch']}</td>
                    <td><span class="status-badge {badge_class}">{conclusion or 'unknown'}</span></td>
                    <td>{time_str}</td>
                    <td><a href="{repo['run_url']}" target="_blank">View Run →</a></td>
                </tr>
"""

html += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

# Create output directory
os.makedirs('output', exist_ok=True)

# Write HTML file
with open('output/index.html', 'w') as f:
    f.write(html)

print(f"\n✅ Dashboard generated successfully!")
print(f"   Repos tracked: {len(dashboard_data)}")