from synapse.app.homeserver import setup, run as main_run

CONFIG_PATH = "./tests/example_cfg.yml"
def run() -> None:
    hs = setup(config_options=["-c", CONFIG_PATH, "--generate-missing-and-run"])
    print("Service available at http://localhost:8091/_synapse/client/super_invites")
    print("Shared secret is: exampleLove")
    main_run(hs)

run()