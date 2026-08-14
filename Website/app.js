import { baseLayerLuminance, StandardLuminance } from 'https://unpkg.com/@fluentui/web-components@2.6.1';

const GROUP_LISTINGS = {
  latest: 'https://omoi0kane.github.io/platform-magazine/listings/latest.json',
  'vol01-05': 'https://omoi0kane.github.io/platform-magazine/listings/vol01-05.json',
  'vol06-10': 'https://omoi0kane.github.io/platform-magazine/listings/vol06-10.json',
  'vol11-15': 'https://omoi0kane.github.io/platform-magazine/listings/vol11-15.json',
  'vol16-20': 'https://omoi0kane.github.io/platform-magazine/listings/vol16-20.json',
  special: 'https://omoi0kane.github.io/platform-magazine/listings/special.json',
};

const listingUrlForPackage = (packageId) => {
  if (packageId === 'net.omoi0kane.platform-magazine.latest') return GROUP_LISTINGS.latest;
  if (packageId.startsWith('net.omoi0kane.platform-magazine.special')) return GROUP_LISTINGS.special;
  const match = packageId.match(/^net\.omoi0kane\.platform-magazine\.vol(\d{2})$/);
  if (!match) throw new Error(`Package is not assigned to a grouped listing: ${packageId}`);
  const volume = Number(match[1]);
  if (volume <= 5) return GROUP_LISTINGS['vol01-05'];
  if (volume <= 10) return GROUP_LISTINGS['vol06-10'];
  if (volume <= 15) return GROUP_LISTINGS['vol11-15'];
  if (volume <= 20) return GROUP_LISTINGS['vol16-20'];
  throw new Error(`Volume is outside the supported range: ${packageId}`);
};

const PACKAGES = {
{{~ for package in packages ~}}
{{~ if package.Name != "net.omoi0kane.platform-magazine" ~}}
  "{{ package.Name }}": {
    name: "{{ package.Name }}",
    displayName: "{{ if package.DisplayName; package.DisplayName; end; }}",
    description: "VRChatワールドに設置して読めるPlatformの冊子です。",
    version: "{{ package.Version }}",
    author: {
      name: "{{ if package.Author.Name; package.Author.Name; end; }}",
      url: "{{ if package.Author.Url; package.Author.Url; end; }}",
    },
    dependencies: {
      {{~ for dependency in package.Dependencies ~}}
        "{{ dependency.Name }}": "{{ dependency.Version }}",
      {{~ end ~}}
    },
    keywords: [
      {{~ for keyword in package.Keywords ~}}
        "{{ keyword }}",
      {{~ end ~}}
    ],
    license: "{{ package.License }}",
    licensesUrl: "{{ package.LicensesUrl }}",
  },
{{~ end ~}}
{{~ end ~}}
};

const setTheme = () => {
  const isDarkTheme = () => window.matchMedia("(prefers-color-scheme: dark)").matches;
  if (isDarkTheme()) {
    baseLayerLuminance.setValueFor(document.documentElement, StandardLuminance.DarkMode);
  } else {
    baseLayerLuminance.setValueFor(document.documentElement, StandardLuminance.LightMode);
  }
}

(() => {
  setTheme();

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    setTheme();
  });

  const packageGrid = document.getElementById('packageGrid');

  const searchInput = document.getElementById('searchInput');
  searchInput.addEventListener('input', ({ target: { value = '' }}) => {
    const items = packageGrid.querySelectorAll('fluent-data-grid-row[row-type="default"]');
    items.forEach(item => {
      if (value === '') {
        item.style.display = 'grid';
        return;
      }
      if (
        item.dataset?.packageName?.toLowerCase()?.includes(value.toLowerCase()) ||
        item.dataset?.packageId?.toLowerCase()?.includes(value.toLowerCase())
      ) {
        item.style.display = 'grid';
      } else {
        item.style.display = 'none';
      }
    });
  });

  const addListingToVccHelp = document.getElementById('addListingToVccHelp');
  const addListingToVccHelpClose = document.getElementById('addListingToVccHelpClose');
  addListingToVccHelpClose.addEventListener('click', () => {
    addListingToVccHelp.hidden = true;
  });

  const groupAddToVccButtons = document.querySelectorAll('.groupAddToVccButton');
  groupAddToVccButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const listingUrl = button.dataset.listingUrl;
      window.location.assign(`vcc://vpm/addRepo?url=${encodeURIComponent(listingUrl)}`);
    });
  });

  const vccListingInfoUrlFieldCopy = document.getElementById('vccListingInfoUrlFieldCopy');
  vccListingInfoUrlFieldCopy.addEventListener('click', () => {
    const vccUrlField = document.getElementById('vccListingInfoUrlField');
    vccUrlField.select();
    navigator.clipboard.writeText(vccUrlField.value);
    vccUrlFieldCopy.appearance = 'accent';
    setTimeout(() => {
      vccUrlFieldCopy.appearance = 'neutral';
    }, 1000);
  });


  const rowMoreMenu = document.getElementById('rowMoreMenu');
  const hideRowMoreMenu = e => {
    if (rowMoreMenu.contains(e.target)) return;
    document.removeEventListener('click', hideRowMoreMenu);
    rowMoreMenu.hidden = true;
  }

  const rowMenuButtons = document.querySelectorAll('.rowMenuButton');
  rowMenuButtons.forEach(button => {
    button.addEventListener('click', e => {
      if (rowMoreMenu?.hidden) {
        rowMoreMenu.style.top = `${e.clientY + e.target.clientHeight}px`;
        rowMoreMenu.style.left = `${e.clientX - 120}px`;
        rowMoreMenu.hidden = false;

        const downloadLink = rowMoreMenu.querySelector('#rowMoreMenuDownload');
        const downloadListener = () => {
          window.open(e?.target?.dataset?.packageUrl, '_blank');
        }
        downloadLink.addEventListener('change', () => {
          downloadListener();
          downloadLink.removeEventListener('change', downloadListener);
        });

        setTimeout(() => {
          document.addEventListener('click', hideRowMoreMenu);
        }, 1);
      }
    });
  });

  const packageInfoModal = document.getElementById('packageInfoModal');
  const packageInfoModalClose = document.getElementById('packageInfoModalClose');
  packageInfoModalClose.addEventListener('click', () => {
    packageInfoModal.hidden = true;
  });

  // Fluent dialogs use nested shadow-rooted elements, so we need to use JS to style them
  const modalControl = packageInfoModal.shadowRoot.querySelector('.control');
  modalControl.style.maxHeight = "90%";
  modalControl.style.transition = 'height 0.2s ease-in-out';
  modalControl.style.overflowY = 'hidden';

  const packageInfoName = document.getElementById('packageInfoName');
  const packageInfoId = document.getElementById('packageInfoId');
  const packageInfoVersion = document.getElementById('packageInfoVersion');
  const packageInfoDescription = document.getElementById('packageInfoDescription');
  const packageInfoAuthor = document.getElementById('packageInfoAuthor');
  const packageInfoDependencies = document.getElementById('packageInfoDependencies');
  const packageInfoKeywords = document.getElementById('packageInfoKeywords');
  const packageInfoLicense = document.getElementById('packageInfoLicense');

  const rowAddToVccButtons = document.querySelectorAll('.rowAddToVccButton');
  rowAddToVccButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const listingUrl = listingUrlForPackage(button.dataset.packageId);
      window.location.assign(`vcc://vpm/addRepo?url=${encodeURIComponent(listingUrl)}`);
    });
  });

  const rowPackageInfoButton = document.querySelectorAll('.rowPackageInfoButton');
  rowPackageInfoButton.forEach((button) => {
    button.addEventListener('click', e => {
      const packageId = e.target.dataset?.packageId;
      const packageInfo = PACKAGES?.[packageId];
      if (!packageInfo) {
        console.error(`Did not find package ${packageId}. Packages available:`, PACKAGES);
        return;
      }

      packageInfoName.textContent = packageInfo.displayName;
      packageInfoId.textContent = packageId;
      packageInfoVersion.textContent = `v${packageInfo.version}`;
      packageInfoDescription.textContent = packageInfo.description;
      packageInfoAuthor.textContent = packageInfo.author.name;
      packageInfoAuthor.href = packageInfo.author.url;
      const groupedListingUrl = listingUrlForPackage(packageId);
      document.getElementById('packageInfoVccUrlField').value = groupedListingUrl;
      document.getElementById('vccListingInfoUrlField').value = groupedListingUrl;

      if ((packageInfo.keywords?.length ?? 0) === 0) {
        packageInfoKeywords.parentElement.classList.add('hidden');
      } else {
        packageInfoKeywords.parentElement.classList.remove('hidden');
        packageInfoKeywords.innerHTML = null;
        packageInfo.keywords.forEach(keyword => {
          const keywordDiv = document.createElement('div');
          keywordDiv.classList.add('me-2', 'mb-2', 'badge');
          keywordDiv.textContent = keyword;
          packageInfoKeywords.appendChild(keywordDiv);
        });
      }

      if (!packageInfo.license?.length && !packageInfo.licensesUrl?.length) {
        packageInfoLicense.parentElement.classList.add('hidden');
      } else {
        packageInfoLicense.parentElement.classList.remove('hidden');
        packageInfoLicense.textContent = packageInfo.license ?? 'See License';
        packageInfoLicense.href = packageInfo.licensesUrl ?? '#';
      }

      packageInfoDependencies.innerHTML = null;
      Object.entries(packageInfo.dependencies).forEach(([name, version]) => {
        const depRow = document.createElement('li');
        depRow.classList.add('mb-2');
        depRow.textContent = `${name} @ v${version}`;
        packageInfoDependencies.appendChild(depRow);
      });

      packageInfoModal.hidden = false;

      setTimeout(() => {
        const height = packageInfoModal.querySelector('.col').clientHeight;
        modalControl.style.setProperty('--dialog-height', `${height + 14}px`);
      }, 1);
    });
  });

  const packageInfoVccUrlFieldCopy = document.getElementById('packageInfoVccUrlFieldCopy');
  packageInfoVccUrlFieldCopy.addEventListener('click', () => {
    const vccUrlField = document.getElementById('packageInfoVccUrlField');
    vccUrlField.select();
    navigator.clipboard.writeText(vccUrlField.value);
    vccUrlFieldCopy.appearance = 'accent';
    setTimeout(() => {
      vccUrlFieldCopy.appearance = 'neutral';
    }, 1000);
  });

  const packageInfoListingHelp = document.getElementById('packageInfoListingHelp');
  packageInfoListingHelp.addEventListener('click', () => {
    addListingToVccHelp.hidden = false;
  });
})();