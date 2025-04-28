
import streamlit as st
import subprocess
import json
import os
from Constants import PROJECT_ROOT


def verify_aws_credentials(aws_access_key_id, aws_secret_access_key, aws_region):
    """Tries a simple AWS CLI command to verify credentials using provided inputs."""
    if not all([aws_access_key_id, aws_secret_access_key, aws_region]):
        st.warning(
            "Please enter AWS Access Key ID, Secret Access Key, and Region.")
        return False

    st.info("Verifying AWS credentials...")
    command = "aws sts get-caller-identity"
    env_vars = {
        "AWS_ACCESS_KEY_ID": aws_access_key_id,
        "AWS_SECRET_ACCESS_KEY": aws_secret_access_key,
        "AWS_DEFAULT_REGION": aws_region
    }
    try:
        # subprocess.run for synchronous verification
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            # Pass credentials in environment
            env={**os.environ, **env_vars}
        )
        st.success("AWS credentials verified successfully!")
        try:
            st.json(json.loads(result.stdout))
        except json.JSONDecodeError:
            # Show raw output if not JSON
            st.text(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        st.error("AWS credential verification failed.")
        st.text("Error output:")
        st.code(e.stderr or e.stdout or "No output captured.")
        st.warning(
            "Please ensure the provided credentials and region are correct.")
        return False
    except FileNotFoundError:
        st.error("AWS CLI command not found. Is it installed and in your PATH?")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred during verification: {str(e)}")
        return False
