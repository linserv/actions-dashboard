#!/usr/bin/env python3
import os
from github import Github, Auth
from datetime import datetime

# Initialize GitHub client with new auth method
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
user_login = os.environ.get('DASHBOARD_USER', 'linservbot')

# Filter for specific workflows (comma-separated, or leave empty for all)
workflow_filter = os.environ.get('WORKFLOW_FILTER', 'sync-fork,sync-odoo,sync-3rd-party').lower()
workflow_filters = [f.strip() for f in workflow_filter.split(',') if f.strip()]

print(f"Workflow filter: {workflow_filters if workflow_filters else 'None (showing all workflows)'}")

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
        
        # Apply workflow filter if specified
        if workflow_filters:
            workflow_name_lower = latest_run.name.lower()
            if not any(filter_term in workflow_name_lower for filter_term in workflow_filters):
                print(f"  ⊘ {repo.full_name}: Skipped (workflow '{latest_run.name}' doesn't match filter)")
                continue
        
        # Determine workflow type/category
        workflow_name_lower = latest_run.name.lower()
        if 'odoo' in workflow_name_lower:
            workflow_type = '🐭 Odoo'
        elif '3rd' in workflow_name_lower or 'third' in workflow_name_lower:
            workflow_type = '📦 3rd Party'
        else:
            workflow_type = '🔄 Other'
        
        # Get jobs for this run (to show matrix details)
        jobs = latest_run.jobs()
        job_details = []
        
        for job in jobs:
            job_details.append({
                'name': job.name,
                'status': job.status,
                'conclusion': job.conclusion,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            })
        
        repo_data = {
            'name': repo.full_name,
            'url': repo.html_url,
            'workflow_name': latest_run.name,
            'workflow_type': workflow_type,
            'status': latest_run.status,
            'conclusion': latest_run.conclusion,
            'run_url': latest_run.html_url,
            'updated_at': latest_run.updated_at.isoformat(),
            'branch': latest_run.head_branch,
            'jobs': job_details,
            'job_count': len(job_details)
        }
        
        dashboard_data.append(repo_data)
        
        # Summary for console
        success_count = sum(1 for j in job_details if j['conclusion'] == 'success')
        failure_count = sum(1 for j in job_details if j['conclusion'] == 'failure')
        
        print(f"  ✓ {repo.full_name}: {latest_run.conclusion or latest_run.status} "
              f"(workflow: {latest_run.name}, jobs: {success_count}✅/{failure_count}❌)")
        
    except Exception as e:
        print(f"  ✗ Error fetching {repo.full_name}: {e}")
        continue

# Sort by status (failed first, then in progress, then success)
# Then by workflow type
status_priority = {'failure': 0, 'cancelled': 1, 'in_progress': 2, 'success': 3, 'completed': 4}
workflow_type_priority = {'🐭 Odoo': 0, '📦 3rd Party': 1, '🔄 Other': 2}

dashboard_data.sort(key=lambda x: (
    workflow_type_priority.get(x['workflow_type'], 99),
    status_priority.get(x['conclusion'] or x['status'], 99)
))

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
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            margin-bottom: 10px;
            color: #58a6ff;
        }}
        h2 {{
            margin-top: 30px;
            margin-bottom: 20px;
            color: #8b949e;
            font-size: 18px;
            padding-bottom: 10px;
            border-bottom: 1px solid #30363d;
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
            margin-bottom: 20px;
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
        .filter-badge {{
            display: inline-block;
            background: #1f6feb;
            color: #fff;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 13px;
            margin-left: 10px;
            font-weight: 500;
        }}
        .job-details {{
            margin-top: 8px;
            padding: 8px;
            background: #0d1117;
            border-radius: 4px;
            font-size: 12px;
        }}
        .job-item {{
            display: inline-block;
            margin-right: 12px;
            padding: 3px 8px;
            border-radius: 3px;
            margin-bottom: 4px;
        }}
        .job-item.success {{
            background: #1a3c25;
            color: #3fb950;
        }}
        .job-item.failure {{
            background: #3c1c1f;
            color: #f85149;
        }}
        .job-item.in_progress {{
            background: #3c2e1a;
            color: #d29922;
        }}
        .job-summary {{
            color: #8b949e;
            font-size: 11px;
            margin-top: 4px;
        }}
        .expandable {{
            cursor: pointer;
        }}
        .expand-icon {{
            display: inline-block;
            margin-right: 5px;
            transition: transform 0.2s;
        }}
        .expanded .expand-icon {{
            transform: rotate(90deg);
        }}
        details {{
            margin-top: 8px;
        }}
        summary {{
            cursor: pointer;
            color: #58a6ff;
            font-size: 12px;
            padding: 4px;
        }}
        summary:hover {{
            text-decoration: underline;
        }}
        .workflow-section {{
            margin-bottom: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 GitHub Actions Dashboard - {user_login}{f'<span class="filter-badge">🔍 {", ".join(workflow_filters)}</span>' if workflow_filters else ''}</h1>
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
"""

# Group by workflow type
workflow_groups = {}
for repo in dashboard_data:
    wf_type = repo['workflow_type']
    if wf_type not in workflow_groups:
        workflow_groups[wf_type] = []
    workflow_groups[wf_type].append(repo)

# Generate tables for each workflow type
for workflow_type in sorted(workflow_groups.keys()):
    repos_in_group = workflow_groups[workflow_type]
    
    html += f"""
        <div class="workflow-section">
            <h2>{workflow_type} - {len(repos_in_group)} repos</h2>
            <table>
                <thead>
                    <tr>
                        <th>Repository</th>
                        <th>Workflow</th>
                        <th>Branch</th>
                        <th>Status</th>
                        <th>Jobs</th>
                        <th>Last Updated</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for repo in repos_in_group:
        conclusion = repo['conclusion'] or repo['status']
        badge_class = f"badge-{conclusion.replace('_', '-')}" if conclusion else "badge-cancelled"
        
        # Format date
        try:
            updated = datetime.fromisoformat(repo['updated_at'].replace('Z', '+00:00'))
            time_str = updated.strftime('%Y-%m-%d %H:%M')
        except:
            time_str = repo['updated_at']
        
        # Job summary
        jobs = repo['jobs']
        success_jobs = sum(1 for j in jobs if j['conclusion'] == 'success')
        failure_jobs = sum(1 for j in jobs if j['conclusion'] == 'failure')
        in_progress_jobs = sum(1 for j in jobs if j['status'] == 'in_progress')
        
        job_summary = f"{success_jobs}✅"
        if failure_jobs > 0:
            job_summary += f" / {failure_jobs}❌"
        if in_progress_jobs > 0:
            job_summary += f" / {in_progress_jobs}⏳"
        
        # Job details HTML
        job_details_html = ""
        if len(jobs) > 1:  # Only show details if there are multiple jobs (matrix)
            job_details_html = "<details><summary>Show job details</summary><div class='job-details'>"
            for job in jobs:
                job_conclusion = job['conclusion'] or job['status']
                job_class = job_conclusion.replace(' ', '_') if job_conclusion else 'unknown'
                job_details_html += f"<span class='job-item {job_class}'>{job['name']}</span>"
            job_details_html += "</div></details>"
        
        html += f"""
                    <tr>
                        <td class="repo-name"><a href="{repo['url']}" target="_blank">{repo['name']}</a></td>
                        <td>{repo['workflow_name']}</td>
                        <td>{repo['branch']}</td>
                        <td><span class="status-badge {badge_class}">{conclusion or 'unknown'}</span></td>
                        <td>
                            <div>{job_summary}</div>
                            {job_details_html}
                        </td>
                        <td>{time_str}</td>
                        <td><a href="{repo['run_url']}" target="_blank">View Run →</a></td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
"""

html += """
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
print(f"   Filter applied: {workflow_filters if workflow_filters else 'None'}")

# Close connection
g.close()
