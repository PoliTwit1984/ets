import json


def convert_local_settings_to_env(local_settings_path, env_path):
    with open(local_settings_path, 'r') as f:
        settings = json.load(f)

    env_lines = []
    for key, value in settings['Values'].items():
        env_lines.append(f"{key}={value}")

    with open(env_path, 'w') as f:
        f.write('\n'.join(env_lines))


if __name__ == "__main__":
    local_settings_path = 'local.settings.json'
    env_path = '.env'
    convert_local_settings_to_env(local_settings_path, env_path)
    print(f"Converted {local_settings_path} to {env_path}")
