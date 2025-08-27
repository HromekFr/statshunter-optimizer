# GitHub Secrets Setup for CI/CD

To enable full testing with real API services in GitHub Actions, configure the following secrets:

## Required Secrets

Add these secrets to your repository to enable full integration testing:

### Setting up Secrets

1. Go to your repository settings: https://github.com/HromekFr/statshunter-optimizer/settings/secrets/actions

2. Click **New repository secret** for each of the following:

### API Keys

#### `STATSHUNTERS_API_KEY`
- **Description**: Statshunters share link or API key
- **How to get**: From your Statshunters profile settings
- **Example value**: `a36657ea68e65e599697cfb42443fddd`
- **Required**: Optional (tests will use mock if not provided)

#### `ORS_API_KEY`
- **Description**: OpenRouteService API key
- **How to get**: 
  1. Sign up at https://openrouteservice.org/dev/#/signup
  2. Get your API key from the dashboard
- **Example format**: `5b3ce35978511100001cf6248...` (long base64 string)
- **Required**: Recommended for full routing tests

#### `MAPY_API_KEY`
- **Description**: Mapy.cz API key for Central European routing
- **How to get**:
  1. Create account at https://developer.mapy.com/account/
  2. Create a new API project
  3. Copy the generated API key
- **Example format**: `7DvT5utpHlMUDGIOJ4sgwHX5cos6CIYAkUQCLBrsnug`
- **Required**: Recommended for Mapy.cz integration tests

## Verifying Secrets

After adding secrets:

1. Check the Actions tab in your repository
2. Re-run any failed workflows
3. Tests should now pass with real API integration

## Security Notes

- Secrets are encrypted and only exposed to GitHub Actions
- Never commit actual API keys to the repository
- Secrets are not available to pull requests from forks
- Rotate keys periodically for security

## Fallback Behavior

If secrets are not configured:
- Tests will use mock/fake API keys
- Some integration tests may be skipped
- Unit tests will still run normally
- CI will still pass but with limited coverage

## Testing Locally with Secrets

To test locally with the same configuration:

```bash
# Create .env file locally (don't commit!)
cp .env.example .env

# Add your real API keys to .env
# Run tests
python -m pytest tests/ -v
```

## Troubleshooting

If tests fail after adding secrets:

1. **Check secret names**: Must match exactly (case-sensitive)
2. **Check API key validity**: Test keys manually first
3. **Check rate limits**: Some APIs have rate limits
4. **Check workflow logs**: GitHub Actions logs show which secrets are available

## Environment-Specific Secrets

You can also set different secrets for different environments:

- `STATSHUNTERS_API_KEY_DEV`: Development environment
- `STATSHUNTERS_API_KEY_PROD`: Production environment

Then use them conditionally in workflows based on branch or event type.