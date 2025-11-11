#!/usr/bin/env python3
import os
from github import Github, Auth
from datetime import datetime

# Initialize GitHub client with new auth method
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
user_login = os.environ.get('DASHBOARD_USER', 'linservbot')

# Filter for specific workflows (comma-separated, or leave empty for all)
workflow_filter = os.environ.get('WORKFLOW_FILTER', 'sync-odoo,sync-3rd-party').lower()
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
            
        # Get ALL workflow runs (not just latest)
        all_runs = repo.get_workflow_runs()
        
        if all_runs.totalCount == 0:
            continue
        
        # Track workflows we've already processed for this repo
        processed_workflows = set()
        
        # Process each run
        for run in all_runs:
            workflow_name_lower = run.name.lower()
            
            # Apply workflow filter if specified
            if workflow_filters:
                if not any(filter_term in workflow_name_lower for filter_term in workflow_filters):
                    continue
            
            # Skip if we already have a run for this workflow in this repo
            # (we want the latest for each workflow)
            if run.name in processed_workflows:
                continue
            
            processed_workflows.add(run.name)
            
            # Determine workflow type/category
            if 'sync-odoo' in workflow_name_lower:
                workflow_type = '🐭 Odoo'
            elif '3rd' in workflow_name_lower or 'third' in workflow_name_lower or 'sync-3rd' in workflow_name_lower:
                workflow_type = '📦 3rd Party'
            else:
                workflow_type = '🔄 Other'
            
            # Get jobs for this run
            jobs = run.jobs()
            job_details = []
            
            for job in jobs:
                job_name = job.name
                
                job_details.append({
                    'name': job_name,
                    'status': job.status,
                    'conclusion': job.conclusion,
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                })
            
            repo_data = {
                'name': repo.full_name,
                'url': repo.html_url,
                'workflow_name': run.name,
                'workflow_type': workflow_type,
                'status': run.status,
                'conclusion': run.conclusion,
                'run_url': run.html_url,
                'updated_at': run.updated_at.isoformat(),
                'branch': run.head_branch,
                'jobs': job_details,
                'job_count': len(job_details)
            }
            
            dashboard_data.append(repo_data)
            
            # Summary for console
            success_count = sum(1 for j in job_details if j['conclusion'] == 'success')
            failure_count = sum(1 for j in job_details if j['conclusion'] == 'failure')
            
            print(f"  ✓ {repo.full_name}: {run.conclusion or run.status} "
                  f"(workflow: {run.name}, jobs: {success_count}✅/{failure_count}❌)")
        
    except Exception as e:
        print(f"  ✗ Error fetching {repo.full_name}: {e}")
        continue

# Sort by status (failed first, then in progress, then success)
# Then by workflow type
status_priority = {'failure': 0, 'cancelled': 1, 'in_progress': 2, 'success': 3, 'completed': 4}
workflow_type_priority = {
    '🐭 Odoo': 0,
    '📦 3rd Party': 1,
    '🔄 Other': 2
}

dashboard_data.sort(key=lambda x: (
    workflow_type_priority.get(x['workflow_type'], 99),
    status_priority.get(x['conclusion'] or x['status'], 99),
    x['name']  # Secondary sort by repo name
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
            max-width: 1600px;
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
            font-size: 13px;
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
        .dashboard-row {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            margin-bottom: 16px;
            padding: 16px;
            transition: background-color 0.2s;
        }}
        .dashboard-row:hover {{
            background: #1c2128;
        }}
        .row-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .repo-info {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
            min-width: 300px;
        }}
        .repo-name {{
            font-weight: 600;
            color: #58a6ff;
        }}
        .branch-badge {{
            background: #1f6feb;
            color: #fff;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
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
        .meta-info {{
            display: flex;
            gap: 16px;
            font-size: 12px;
            color: #8b949e;
            flex-wrap: wrap;
        }}
        .meta-item {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        a {{
            color: #58a6ff;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .job-summary {{
            font-size: 12px;
            color: #c9d1d9;
            font-weight: 500;
        }}
        .jobs-container {{
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #30363d;
        }}
        .jobs-title {{
            font-size: 12px;
            font-weight: 600;
            color: #8b949e;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .job-list {{
            display: grid;
            gap: 8px;
        }}
        .job-item {{
            background: #0d1117;
            border-radius: 4px;
            padding: 10px 12px;
            border-left: 3px solid;
            display: flex;
            flex-direction: column;
            gap: 6px;
            font-size: 12px;
        }}
        .job-item.success {{
            border-left-color: #3fb950;
            background: rgba(63, 185, 80, 0.1);
        }}
        .job-item.failure {{
            border-left-color: #f85149;
            background: rgba(248, 81, 73, 0.1);
        }}
        .job-item.in_progress {{
            border-left-color: #d29922;
            background: rgba(210, 153, 34, 0.1);
        }}
        .job-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .job-name {{
            flex: 1;
            word-break: break-word;
            font-weight: 500;
        }}
        .job-status {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            white-space: nowrap;
        }}
        .job-status.success {{
            background: rgba(63, 185, 80, 0.2);
            color: #3fb950;
        }}
        .job-status.failure {{
            background: rgba(248, 81, 73, 0.2);
            color: #f85149;
        }}
        .job-status.in_progress {{
            background: rgba(210, 153, 34, 0.2);
            color: #d29922;
        }}
        .branches-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        .branch-item {{
            background: rgba(88, 166, 255, 0.15);
            border: 1px solid rgba(88, 166, 255, 0.3);
            color: #58a6ff;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
        }}
        .branch-item.success {{
            background: rgba(63, 185, 80, 0.15);
            border-color: rgba(63, 185, 80, 0.3);
            color: #3fb950;
        }}
        .branch-item.failure {{
            background: rgba(248, 81, 73, 0.15);
            border-color: rgba(248, 81, 73, 0.3);
            color: #f85149;
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
                <div class="stat-label">Total Runs</div>
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

# Generate sections for each workflow type
for workflow_type in sorted(workflow_groups.keys(), key=lambda x: workflow_type_priority.get(x, 99)):
    repos_in_group = workflow_groups[workflow_type]
    
    html += f"""
        <div class="workflow-section">
            <h2>{workflow_type} - {len(repos_in_group)} runs</h2>
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
        
        # Build jobs HTML with branches extracted from job names
        jobs_html = ""
        if len(jobs) > 0:
            jobs_html = '<div class="jobs-container">'
            jobs_html += '<div class="jobs-title">📊 Job Details</div>'
            jobs_html += '<div class="job-list">'
            
            for job in jobs:
                job_conclusion = job['conclusion'] or job['status']
                job_class = job_conclusion.replace(' ', '_').replace('-', '_') if job_conclusion else 'unknown'
                
                job_display_name = job['name']
                if 'Sync' in job['name']:
                    parts = job['name'].replace('Sync', '').strip()
                    job_display_name = f"<strong>{parts}</strong>"
                
                status_badge = f'<span class="job-status {job_class}">{"✅ success" if job_conclusion == "success" else "❌ failed" if job_conclusion == "failure" else "⏳ in progress"}</span>'
                
                jobs_html += f'''
                    <div class="job-item {job_class}">
                        <div class="job-header">
                            <span class="job-name">{job_display_name}</span>
                            {status_badge}
                        </div>
                    </div>
                '''
            
            jobs_html += '</div></div>'
        
        html += f"""
            <div class="dashboard-row">
                <div class="row-header">
                    <div class="repo-info">
                        <span class="repo-name"><a href="{repo['url']}" target="_blank">📁 {repo['name']}</a></span>
                        <span class="branch-badge">🌿 {repo['branch']}</span>
                    </div>
                    <span class="status-badge {badge_class}">{conclusion.upper()}</span>
                </div>
                <div class="meta-info">
                    <div class="meta-item">
                        <span>Workflow:</span>
                        <strong>{repo['workflow_name']}</strong>
                    </div>
                    <div class="meta-item">
                        <span>Jobs:</span>
                        <strong class="job-summary">{job_summary}</strong>
                    </div>
                    <div class="meta-item">
                        <span>Updated:</span>
                        <strong>{time_str}</strong>
                    </div>
                    <div class="meta-item">
                        <a href="{repo['run_url']}" target="_blank">View Run →</a>
                    </div>
                </div>
                {jobs_html}
            </div>
"""
    
    html += """
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
print(f"   Total runs tracked: {len(dashboard_data)}")
print(f"   Filter applied: {workflow_filters if workflow_filters else 'None'}")

# Close connection
g.close()
