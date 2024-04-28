# Vesta

[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

This custom component integrates with the Gizwits cloud API, providing control of devices such as Vesta sous vide immersion cooker.

## Required Account

You must have an account with the Vesta mobile app ([Android][vesta-android]/[iOS][vesta-ios]). Lay-Z-Spa app credentials will not work. Both apps appear to have identical feature sets.

Vesta usually uses the US API endpoints. If you get an error stating account could not be found, try using the other endpoint. If this does not help, then create a new account under a supported country.


## Device Support

A Wi-Fi enabled model is required. No custom hardware is required. Configure the Wi-Fi on the device using the mobile app.

## Installation

This integration is delivered as a HACS custom repository.

1. Download and install [HACS][hacs-download].
2. Add a [custom repository][hacs-custom] in HACS. You will need to enter the URL of this repository when prompted: `https://github.com/fcolasuonno/ha-vesta`.

## Configuration

Ensure you can control your device using the Vesta mobile app.

* Go to **Configuration** > **Devices & Services** > **Add Integration**, then find **Vesta** in the list.
* Enter your Vesta username and password when prompted.

## Acknowledgements

* https://github.com/B-Hartley/bruces_homeassistant_config
* https://github.com/cdpuk/ha-bestway
* https://github.com/brendann993/pyGizwits

## Contributing

If you want to contribute to this please read the [Contribution Guidelines](CONTRIBUTING.md).

[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/fcolasuonno/ha-vesta.svg?style=for-the-badge
[hacs-download]: https://hacs.xyz/docs/setup/download
[hacs-custom]: https://hacs.xyz/docs/faq/custom_repositories
[vesta-android]: https://play.google.com/store/apps/details?id=com.youhone.vesta
[vesta-ios]: https://apps.apple.com/app/vesta-sous-vide/id1436096850