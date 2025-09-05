import os
import requests
import sys
import json

# ---- ADO Config ----
ADO_ORG = os.getenv("ADO_ORG")  # e.g. 'myorg'
ADO_PAT = os.getenv("ADO_PAT")

# ---- Blueprint Identifiers ----
BLUEPRINT_ENV = os.getenv("BLUEPRINT_ENV", "azure_dev_ops_environment")
BLUEPRINT_DEPLOYMENT = os.getenv("BLUEPRINT_DEPLOYMENT", "azure_dev_ops_deployment")

# ---- Port Auth Helpers ----
PORT_CLIENT_ID = os.getenv("PORT_CLIENT_ID")
PORT_CLIENT_SECRET = os.getenv("PORT_CLIENT_SECRET")

BASE_URL = "https://api.getport.io/v1"


def get_port_token():
    """Authenticate to Port and return an access token using env vars PORT_CLIENT_ID and PORT_CLIENT_SECRET."""
    if not PORT_CLIENT_ID or not PORT_CLIENT_SECRET:
        raise EnvironmentError(
            "Please set PORT_CLIENT_ID and PORT_CLIENT_SECRET environment variables."
        )
    url = "https://api.getport.io/v1/auth/access_token"
    payload = {"clientId": PORT_CLIENT_ID, "clientSecret": PORT_CLIENT_SECRET}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        token = response.json().get("accessToken")
        if not token:
            raise ValueError("No accessToken found in Port API response.")
        return token
    except requests.exceptions.RequestException as e:
        print(f"Error requesting Port access token: {e}")
        raise
    except (ValueError, KeyError) as e:
        print(f"Error parsing Port access token response: {e}")
        raise


def get_port_auth_header():
    """Return a dict with the Authorization header for Port API requests."""
    token = get_port_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---- Port get all blueprints ----
def get_blueprints():
    """Fetch all blueprints from Port."""
    url = f"{BASE_URL}/blueprints"
    headers = get_port_auth_header()
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("data") or response.json().get("blueprints")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching blueprints from Port: {e}")
        raise
    except (ValueError, KeyError) as e:
        print(f"Error parsing blueprints response from Port: {e}")
        raise


# ---- Port Entity Upsert Helper ----
def upsert_port_entity(blueprint_identifier, entity_payload):
    """
    Upsert an entity into Port using the /v1/blueprints/{blueprint_identifier}/entities endpoint.
    Sets upsert=true and create_missing_related_entities=false.
    """
    url = f"https://api.getport.io/v1/blueprints/{blueprint_identifier}/entities?upsert=true"
    headers = get_port_auth_header()
    response = requests.post(url, headers=headers, json=entity_payload)
    response.raise_for_status()
    return response.json()


# Check required env vars
if not (ADO_ORG and ADO_PAT):
    print("Please set ADO_ORG and ADO_PAT environment variables.")
    sys.exit(1)

def get_ado_projects():
    """
    Fetch all projects in the Azure DevOps organization.
    """
    url = f"https://dev.azure.com/{ADO_ORG}/_apis/projects?api-version=7.1"
    response = requests.get(url, auth=("", ADO_PAT))
    response.raise_for_status()
    return response.json().get("value", [])

def get_environments_for_project(project_id):
    """
    Fetch all environments for a given Azure DevOps project.
    """
    url = f"https://dev.azure.com/{ADO_ORG}/{project_id}/_apis/distributedtask/environments?api-version=7.1"
    response = requests.get(url, auth=("", ADO_PAT))
    response.raise_for_status()
    return response.json()

def get_deployment_records_for_project(project_id, env_id):
    """
    Fetch deployment records for a specific environment ID in a given project.
    """
    url = f"https://dev.azure.com/{ADO_ORG}/{project_id}/_apis/distributedtask/environments/{env_id}/environmentdeploymentrecords?api-version=7.1"
    response = requests.get(url, auth=("", ADO_PAT))
    response.raise_for_status()
    return response.json()

def main():
    print("Starting Azure DevOps Environments and Deployments sync to Port...")
    # validate blueprints exist
    print("Validating blueprints...")
    bps = get_blueprints()
    for bp in bps:
        if bp.get("identifier") == BLUEPRINT_ENV:
            print(f"Found environment blueprint: {bp.get('identifier')}")
        if bp.get("identifier") == BLUEPRINT_DEPLOYMENT:
            print(f"Found deployment blueprint: {bp.get('identifier')}")

    print("Fetching Azure DevOps Projects...")
    projects = get_ado_projects()
    environments = []
    deployments = []
    for project in projects:
        project_id = project.get("name")
        print(f"Processing project: {project_id}")
        envs = get_environments_for_project(project_id)
        if "value" in envs:
            for env in envs["value"]:
                env_id = env.get("id")
                env_name = env.get("name")
                payload = {
                    "identifier": str(env_id),
                    "title": env_name,
                    "properties": {},
                    "team": [],
                    "relations": {
                        "project": env.get("project", {}).get("id"),
                        "pipeline": [],
                    },
                }
                environments.append(payload)
                print(f"Processing environment ID: {env_id} in project {project_id}")
                records = get_deployment_records_for_project(project_id, env_id)
                if records.get("value"):
                    for record in records["value"]:
                        deploy_id = record.get("id")
                        build_id = record.get("owner", {}).get("id")
                        pipeline_id = record.get("definition", {}).get("id")
                        payload = {
                            "identifier": str(deploy_id),
                            "title": f"{env_name}-{deploy_id}",
                            "properties": {},
                            "team": [],
                            "relations": {
                                "environment": str(env_id),
                                "pipeline": str(pipeline_id),
                                "build": str(build_id),
                            },
                        }
                        deployments.append(payload)
                        for e in environments:
                            if e["identifier"] == str(env_id):
                                if str(pipeline_id) not in e["relations"]["pipeline"]:
                                    e["relations"]["pipeline"].append(str(pipeline_id))
    print("Begin Upserting Environments and Deployments to Port...")
    for env in environments:
        print(f"Upserting environment {env['title']}...")
        try:
            upsert_port_entity(BLUEPRINT_ENV, env)
        except Exception as e:
            print(f"Error upserting environment {env['title']}: {e}")
    for deploy in deployments:
        print(f"Upserting deployment {deploy['title']}...")
        try:
            upsert_port_entity(BLUEPRINT_DEPLOYMENT, deploy)
        except Exception as e:
            print(f"Error upserting deployment {deploy['title']}: {e}")
    print("Sync complete.")

if __name__ == "__main__":
    main()
