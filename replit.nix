{pkgs}: {
  deps = [
    pkgs.poppler_utils
    pkgs.tesseract
    pkgs.glibcLocales
    pkgs.freetype
    pkgs.postgresql
    pkgs.openssl
  ];
}
