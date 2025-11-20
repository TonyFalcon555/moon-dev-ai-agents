from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Falcon Finance API Docs", docs_url=None, redoc_url=None)

@app.get("/", response_class=HTMLResponse)
async def get_docs():
    return """
    <!doctype html>
    <html>
      <head>
        <title>Falcon Finance API Reference</title>
        <meta charset="utf-8" />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1"
        />
        <style>
          body {
            margin: 0;
          }
        </style>
      </head>
      <body>
        <script
          id="api-reference"
          data-url="/openapi.json"
          data-proxy-url="https://proxy.scalar.com"
        ></script>
        <script>
          var configuration = {
            theme: 'purple',
            spec: {
                content: null,
                url: null,
            },
            tabs: {
                "API Gateway": {
                    url: "http://localhost:8010/openapi.json"
                },
                "Alerts Service": {
                    url: "http://localhost:8012/openapi.json"
                },
                "Dashboard": {
                    url: "http://localhost:8002/openapi.json"
                }
            }
          }
          
          // Scalar configuration for multi-spec is a bit specific, 
          // simpler approach for now is a landing page or just one spec.
          // But let's try to use the standalone script with multiple spec URLs if supported,
          // or just hardcode the script to load one and provide a dropdown in a custom UI?
          
          // Actually, Scalar's CDN script supports a `spec-url` attribute.
          // To keep it simple and robust for this phase, let's just serve a landing page 
          // that links to the individual Swagger UIs, or use a simple multi-spec viewer.
          
          // Let's try a simpler approach: A nice landing page linking to the services.
        </script>
        
        <!-- Reverting to a nice landing page for stability -->
        <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px; text-align: center;">
            <h1 style="color: #6366f1; font-size: 3rem; margin-bottom: 10px;">Falcon Finance API</h1>
            <p style="color: #64748b; font-size: 1.2rem; margin-bottom: 40px;">Unified API Reference & Documentation</p>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
                <a href="http://localhost:8010/docs" target="_blank" style="text-decoration: none; color: inherit;">
                    <div style="border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; transition: transform 0.2s; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
                        <h2 style="margin-top: 0;">🚪 API Gateway</h2>
                        <p style="color: #64748b;">Authentication, Plans, and Key Management.</p>
                        <span style="color: #6366f1; font-weight: 500;">View Docs &rarr;</span>
                    </div>
                </a>
                
                <a href="http://localhost:8012/docs" target="_blank" style="text-decoration: none; color: inherit;">
                    <div style="border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; transition: transform 0.2s; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
                        <h2 style="margin-top: 0;">🔔 Alerts Service</h2>
                        <p style="color: #64748b;">Real-time market alerts and notifications.</p>
                        <span style="color: #6366f1; font-weight: 500;">View Docs &rarr;</span>
                    </div>
                </a>
                
                <a href="http://localhost:8002/docs" target="_blank" style="text-decoration: none; color: inherit;">
                    <div style="border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; transition: transform 0.2s; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
                        <h2 style="margin-top: 0;">📊 Dashboard</h2>
                        <p style="color: #64748b;">Backtesting stats and visualization APIs.</p>
                        <span style="color: #6366f1; font-weight: 500;">View Docs &rarr;</span>
                    </div>
                </a>
            </div>
            
            <p style="margin-top: 60px; color: #94a3b8; font-size: 0.9rem;">
                Powered by Falcon Finance AI Agents
            </p>
        </div>
      </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
