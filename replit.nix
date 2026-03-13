{ pkgs }: {
    deps = [
        pkgs.python310
        pkgs.python310Packages.pip
        pkgs.python310Packages.fastapi
        pkgs.python310Packages.uvicorn
        pkgs.python310Packages.pydantic
    ];
    env = {
        PYTHONUNBUFFERED = "1";
    };
}
