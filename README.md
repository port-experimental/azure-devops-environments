# Azure DevOps Environments Fetcher

This script fetches the list of Azure DevOps Environments for a given organization and project using a Personal Access Token (PAT).

## What does this script do?

This script automates the discovery and ingestion of Azure DevOps environments and deployments for all projects in a given organization. It:

- Fetches a list of all projects in your Azure DevOps organization
- For each project, retrieves all environments and their deployment records
- Prepares environment and deployment data for ingestion into Port
- Upserts the environments and deployments into Port using the Port API and blueprints you define

This enables you to keep your Port catalog in sync with your Azure DevOps infrastructure, providing visibility and automation for environments and deployments across all projects.

## Prerequisites

- Python 3.x
- `requests` library (`pip install requests`)
- An Azure DevOps PAT with appropriate permissions

## Assumptions

- Builds for the deployments/environments exist with their identifier being the ID or the build

## Setup

Set the following environment variables:

- `ADO_ORG`: Your Azure DevOps organization name (e.g., `myorg`)
- `ADO_PAT`: Your Azure DevOps Personal Access Token

Example (Linux/macOS):

```sh
export ADO_ORG="myorg"
export ADO_PAT="your_pat_token"
```

# Additional environment variables for Port integration

- `PORT_CLIENT_ID`: Your Port API client ID
- `PORT_CLIENT_SECRET`: Your Port API client secret
- `BLUEPRINT_ENV`: (Optional) Port blueprint identifier for environments (default: `azure_dev_ops_environment`)
- `BLUEPRINT_DEPLOYMENT`: (Optional) Port blueprint identifier for deployments (default: `azure_dev_ops_deployment`)

## Usage

You can run the script in two ways:

1. To process all projects in your organization:
```sh
python get_ado_environments.py
```

2. To process only specific projects:
   - Create a file named `projects.txt` in the same directory as the script
   - Add one project name per line in the file. Project names are case sensitive.
   - Run the script as normal:
   ```sh
   python get_ado_environments.py
   ```

Example projects.txt:
```
MyProject1
MyProject2
MyProject3
```

If projects.txt exists, the script will only process the projects listed in the file that exist in your Azure DevOps organization. If the file doesn't exist or is empty, the script will process all projects in your organization.

## Creating Port Blueprints

Blueprint definitions for Port can be found in the `blueprints/` folder. To create these blueprints in your Port organization:

1. Log in to your Port admin console.
2. Navigate to the Blueprints section.
3. Use the UI to create a new blueprint, or use the Port API to import the blueprint definition.

### Using the Port API

You can create a blueprint by sending a POST request to the Port API:

```sh
curl -X POST \
  https://api.getport.io/v1/blueprints \
  -H "Authorization: Bearer <YOUR_PORT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d @blueprints/<blueprint-file>.json
```

Replace `<YOUR_PORT_TOKEN>` with your Port API token and `<blueprint-file>.json` with the relevant blueprint file from the `blueprints/` directory (e.g., `azure_dev_ops_environment.json`).

Repeat for each blueprint file you want to create.

For more details, see the [Port API documentation](https://docs.port.io/api-reference/create-a-blueprint).
