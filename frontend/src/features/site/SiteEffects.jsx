import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { brand } from './config';
import { usePlatform } from '@/shared/context/platform';

export default function SiteEffects() {
  const { pathname } = useLocation();
  const { catalog } = usePlatform();
  const contact = catalog?.contact;
  useEffect(() => {
    const canonical = new URL(pathname, brand.site).href;
    let link = document.querySelector('link[rel=canonical]');
    if (!link) { link = document.createElement('link'); link.rel = 'canonical'; document.head.append(link); }
    link.href = canonical;
    const updatePreview = () => {
      const values = { 'og:title': document.title, 'og:description': document.querySelector('meta[name="description"]')?.content || '', 'og:type': 'website', 'og:url': canonical, 'og:image': new URL('/logo.png', brand.site).href };
      for (const [property, content] of Object.entries(values)) {
        let meta = document.querySelector(`meta[property="${property}"]`);
        if (!meta) { meta = document.createElement('meta'); meta.setAttribute('property', property); document.head.append(meta); }
        meta.content = content;
      }
    };
    updatePreview();
    // Lazy pages may set their title after the surrounding layout's effect.
    const observer = new MutationObserver(records => {
      if (records.some(({ target }) => target.nodeName === 'TITLE' || target.parentElement?.nodeName === 'TITLE' || target.matches?.('meta[name="description"]'))) updatePreview();
    });
    observer.observe(document.head, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['content'] });
    if (contact) {
      let organization = document.querySelector('#quantnest-organization');
      if (!organization) { organization = document.createElement('script'); organization.id = 'quantnest-organization'; organization.type = 'application/ld+json'; document.head.append(organization); }
      organization.textContent = JSON.stringify({ '@context': 'https://schema.org', '@type': 'Organization', name: contact.name, url: brand.site, email: contact.email });
    }
    return () => observer.disconnect();
  }, [pathname, contact]);
  return null;
}
