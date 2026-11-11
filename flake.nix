{
  description = "Smart Student Performance & Prediction System";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = {
    self,
    nixpkgs,
  }: let
    system = "x86_64-linux";
    pkgs = import nixpkgs {inherit system;};
    pythonEnv = pkgs.python3.withPackages (
      ps:
        with ps; [
          flask
          flask-sqlalchemy
          scikit-learn
          pandas
          numpy
          faskl-wtf
        ]
    );
  in {
    devShells.${system}.default = pkgs.mkShell {
      packages = [pythonEnv];
      shellHook = ''
        echo "Smart Student Performance System dev shell"
        echo "Run: python scripts/train_model.py && FLASK_APP=app flask run"
      '';
    };
  };
}
