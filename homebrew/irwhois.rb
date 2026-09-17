# Homebrew formula for irwhois.
# Until the homebrew-tap repo exists, install directly from this file:
#   brew install --build-from-source \
#     https://raw.githubusercontent.com/Omidsp79/irwhois/main/homebrew/irwhois.rb
# On a new release: bump `url` + `sha256` below
# (sha256 of the PyPI sdist, see https://pypi.org/project/irwhois/#files).
class Irwhois < Formula
  include Language::Python::Virtualenv

  desc "Check .ir domain availability via whois.nic.ir"
  homepage "https://github.com/Omidsp79/irwhois"
  url "https://files.pythonhosted.org/packages/67/a6/d6afd71fe8e98fb3e0a165a00fe07005c0c4c6f67db2ba9da29cef1f1316/irwhois-1.0.1.tar.gz"
  sha256 "f113ace9e44595828bea1567441dfcc02f0cc7f5a546a24bfa69029d58c7ba80"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "irwhois", shell_output("#{bin}/irwhois --version")
    assert_match "رزرو", shell_output("#{bin}/irwhois fa.ir --no-color")
  end
end
