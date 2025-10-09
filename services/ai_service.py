"""
AI Script Generation Service
Uses OpenAI or Anthropic to generate Turkish video scripts
"""

import os
from typing import Dict
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

class AIService:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        if self.openai_key:
            self.client = AsyncOpenAI(api_key=self.openai_key)
            self.provider = "openai"
        elif self.anthropic_key:
            self.client = AsyncAnthropic(api_key=self.anthropic_key)
            self.provider = "anthropic"
        else:
            self.provider = "demo"
    
    async def generate_turkish_script(self, content_data: Dict, style: str) -> str:
        """Generate a 10-minute Turkish video script"""
        
        if self.provider == "demo":
            return self._generate_demo_script(content_data)
        
        # Determine content type and build appropriate prompt
        content_type = content_data.get('type', 'github_repo')
        
        if content_type == 'github_repo':
            # GitHub repository prompt
            prompt = f"""
GitHub projesi için 10 dakikalık Türkçe eğitim videosu scripti oluştur.

Proje Bilgileri:
- İsim: {content_data.get('name', 'Bilinmiyor')}
- Açıklama: {content_data.get('description', 'Açıklama yok')}
- Programlama Dili: {content_data.get('language', 'Belirtilmemiş')}
- Yıldız Sayısı: {content_data.get('stars', 0)}
- Fork Sayısı: {content_data.get('forks', 0)}
- Konular: {', '.join(content_data.get('topics', [])[:5])}
- Lisans: {content_data.get('license', 'Belirtilmemiş')}

README Özeti:
{content_data.get('readme', 'README bulunamadı')[:1500]}

Gereksinimler:
1. Toplam süre: Tam 10 dakika (yaklaşık 1500-1800 kelime)
2. Dil: Türkçe, profesyonel ama samimi
3. Stil: {style} (tutorial/review/quick_start)
4. Yapı:
   [00:00-00:30] AÇILIŞ - Projeyi tanıt, ne öğreneceklerini söyle
   [00:30-02:00] PROJE TANITIMI - Detaylı açıklama
   [02:00-02:20] GEÇİŞ 1 - Özelliklere geçiş
   [02:20-05:00] ANA ÖZELLİKLER - 3-4 ana özellik detaylı
   [05:00-05:20] GEÇİŞ 2 - Demo'ya geçiş
   [05:20-08:00] DEMO VE KULLANIM - Pratik örnekler
   [08:00-08:20] GEÇİŞ 3 - Kuruluma geçiş
   [08:20-09:30] KURULUM REHBERİ - Adım adım kurulum
   [09:30-10:00] KAPANIŞ - Özet ve vedalaşma

5. Her bölüm başlangıcında [timestamp] BAŞLIK formatında yaz
6. AÇILIŞ, GEÇİŞ ve KAPANIŞ bölümleri avatar ile çekilecek
7. Diğer bölümler ekran kaydı ile çekilecek
8. Doğal, akıcı ve eğitici bir dil kullan
9. Teknik terimleri açıkla
10. İzleyiciyle bağ kur (sorular sor, örnekler ver)

Script'i şimdi oluştur:
"""
        else:
            # General website prompt
            title = content_data.get('title', 'Web Sitesi')
            description = content_data.get('description', '')
            main_content = content_data.get('content', '')[:2000]
            headings = content_data.get('headings', [])
            headings_text = '\n'.join([f"- {h.get('text', '')}" for h in headings[:10]])
            
            prompt = f"""
Bir web sitesi hakkında 10 dakikalık Türkçe eğitim/tanıtım videosu scripti oluştur.

Web Sitesi Bilgileri:
- Başlık: {title}
- URL: {content_data.get('url', '')}
- Açıklama: {description}

Ana Başlıklar:
{headings_text}

İçerik Özeti:
{main_content}

Gereksinimler:
1. Toplam süre: Tam 10 dakika (yaklaşık 1500-1800 kelime)
2. Dil: Türkçe, profesyonel ama samimi
3. Stil: {style} (tutorial/review/quick_start)
4. Yapı:
   [00:00-00:30] AÇILIŞ - Web sitesini tanıt, ne öğreneceklerini söyle
   [00:30-02:00] SİTE TANITIMI - Detaylı açıklama, ne yapıyor, kimler kullanıyor
   [02:00-02:20] GEÇİŞ 1 - Ana özelliklere geçiş
   [02:20-05:00] ANA ÖZELLİKLER - Web sitesinin 3-4 ana özelliği detaylı
   [05:00-05:20] GEÇİŞ 2 - Kullanıma geçiş
   [05:20-08:00] KULLANIM VE ÖRNEKLERİ - Nasıl kullanılır, pratik örnekler
   [08:00-08:20] GEÇİŞ 3 - İpuçlarına geçiş
   [08:20-09:30] İPUÇLARI VE ÖNERİLER - Faydalı ipuçları, püf noktalar
   [09:30-10:00] KAPANIŞ - Özet ve vedalaşma

5. Her bölüm başlangıcında [timestamp] BAŞLIK formatında yaz
6. AÇILIŞ, GEÇİŞ ve KAPANIŞ bölümleri avatar ile çekilecek
7. Diğer bölümler ekran kaydı ile çekilecek
8. Doğal, akıcı ve eğitici bir dil kullan
9. Teknik terimleri açıkla
10. İzleyiciyle bağ kur (sorular sor, örnekler ver)

Script'i şimdi oluştur:
"""
        
        if self.provider == "openai":
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sen profesyonel Türkçe video scripti yazan bir AI asistanısın. Eğitici, samimi ve akıcı scriptler yazarsın."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2500
            )
            content = response.choices[0].message.content
            return content if content else self._generate_demo_script(content_data)
        
        elif self.provider == "anthropic":
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2500,
                temperature=0.7,
                system="Sen profesyonel Türkçe video scripti yazan bir AI asistanısın. Eğitici, samimi ve akıcı scriptler yazarsın.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            for block in response.content:
                if hasattr(block, 'text'):
                    return block.text
            return self._generate_demo_script(content_data)
        
        return self._generate_demo_script(content_data)
    
    def _generate_demo_script(self, content_data: Dict) -> str:
        """Generate demo script when no API key is available"""
        
        content_type = content_data.get('type', 'github_repo')
        
        if content_type == 'github_repo':
            topics_str = ', '.join(content_data.get('topics', [])[:3]) if content_data.get('topics') else 'web geliştirme, API entegrasyonu'
            name = content_data.get('name', 'Proje')
            description = content_data.get('description', 'Açık kaynak proje')
            language = content_data.get('language', 'Python')
            stars = content_data.get('stars', 0)
            forks = content_data.get('forks', 0)
            license_info = content_data.get('license', 'MIT')
            owner = content_data.get('owner', 'developer')
            repo = content_data.get('repo', 'project')
        else:
            # Website content
            name = content_data.get('title', 'Web Sitesi')
            description = content_data.get('description', 'İlginç bir web sitesi')
            topics_str = 'web teknolojileri, dijital platformlar'
            language = 'Web'
            stars = 0
            forks = 0
            license_info = 'N/A'
            owner = ''
            repo = ''
        
        return f"""[00:00-00:30] AÇILIŞ
Merhaba! Bugün {name} {'projesini' if content_type == 'github_repo' else 'sitesini'} detaylıca inceleyeceğiz. 
{description}

Bu videoda neler öğreneceksiniz?
✓ {name} nedir ve nasıl çalışır
✓ Ana özellikleri nelerdir
✓ Nasıl {'kurulur ve' if content_type == 'github_repo' else ''} kullanılır

Hadi başlayalım!

[00:30-02:00] {'PROJE' if content_type == 'github_repo' else 'SİTE'} TANITIMI
{name}, {description}

{'GitHub\'da ' + str(stars) + ' yıldız almış popüler bir açık kaynak projedir.' if content_type == 'github_repo' and stars > 0 else ''}

Bu {'proje' if content_type == 'github_repo' else 'site'} özellikle şu alanlarda kullanılıyor:
• {topics_str}

{str(forks) + ' fork ile aktif bir geliştirici topluluğuna sahip.' if content_type == 'github_repo' and forks > 0 else ''}
{'Proje ' + license_info + ' lisansı altında dağıtılıyor.' if content_type == 'github_repo' and license_info != 'N/A' else ''}

[02:00-02:20] GEÇİŞ 1
Şimdi bu {'projenin' if content_type == 'github_repo' else 'sitenin'} ana özelliklerine detaylı bir şekilde bakalım...

[02:20-05:00] ANA ÖZELLİKLER
Özellik 1: Kolay Kullanım ve Entegrasyon
{name} çok basit ve anlaşılır {'bir API\'ye' if content_type == 'github_repo' else 'bir arayüze'} sahip. 
{'Birkaç satır kod ile projenize entegre edebilirsiniz.' if content_type == 'github_repo' else 'Kullanıcı dostu tasarımı ile kolayca kullanabilirsiniz.'}
{'Dokümantasyon oldukça kapsamlı ve örneklerle desteklenmiş.' if content_type == 'github_repo' else 'Her şey düzenli ve anlaşılır şekilde sunulmuş.'}

Özellik 2: Yüksek Performans {'ve Güvenilirlik' if content_type != 'github_repo' else ''}
{'Proje, optimize edilmiş kod yapısı sayesinde yüksek performans sağlıyor.' if content_type == 'github_repo' else 'Site, modern teknolojilerle hızlı ve güvenilir çalışıyor.'}
{language + ' dilinin avantajlarından tam anlamıyla yararlanıyor.' if content_type == 'github_repo' else 'Kullanıcı deneyimi her zaman öncelikli.'}

Özellik 3: {'Geniş Topluluk Desteği' if content_type == 'github_repo' else 'Zengin İçerik'}
{str(forks) + ' fork ve aktif bir geliştirici topluluğu.' if content_type == 'github_repo' and forks > 0 else 'Çeşitli içerikler ve kaynaklar sunuyor.'}
Sorunlarınıza hızlı çözüm bulabilir, yeni özellikler önerebilirsiniz.

Özellik 4: Sürekli Güncellemeler
Proje düzenli olarak güncelleniyor ve yeni özellikler ekleniyor.
Güvenlik güncellemeleri hızlı bir şekilde yayınlanıyor.

[05:00-05:20] GEÇİŞ 2
Şimdi {'canlı bir demo ile' if content_type == 'github_repo' else ''} {name}{'\'ın' if content_type == 'github_repo' else '\'nin'} nasıl çalıştığını görelim...

[05:20-08:00] {'DEMO VE' if content_type == 'github_repo' else ''} KULLANIM
Gerçek bir kullanım senaryosu üzerinden {name}{'\'ı' if content_type == 'github_repo' else '\'yi'} inceleyelim.

Öncelikle basit bir örnek ile başlayalım.
Bu örnekte projenin temel işlevselliğini göreceğiz.

İlk adımda gerekli bağımlılıkları yüklüyoruz.
Ardından konfigürasyon ayarlarını yapıyoruz.

Şimdi ana işlevselliği kullanalım.
Gördüğünüz gibi kod oldukça basit ve anlaşılır.

Çıktıyı incelediğimizde başarılı bir şekilde çalıştığını görüyoruz.

Şimdi daha gelişmiş bir örneğe bakalım.
Bu örnekte projenin daha ileri seviye özelliklerini kullanacağız.

[08:00-08:20] GEÇİŞ 3
Artık {name}{'\'ı kendi projenize nasıl kuracağınızı' if content_type == 'github_repo' else '\'den nasıl en iyi şekilde faydalanacağınızı'} görelim...

[08:20-09:30] {'KURULUM REHBERİ' if content_type == 'github_repo' else 'İPUÇLARI VE ÖNERİLER'}
{name}{'\'ı kurmak' if content_type == 'github_repo' else '\'den en iyi şekilde yararlanmak'} oldukça basit. {'Adım adım gidelim.' if content_type == 'github_repo' else 'İşte ipuçları:'}

{'''Öncelikle sisteminizde şu gereksinimlerin olduğundan emin olun:
• ''' + language + ''' kurulu olmalı
• Git kurulu olmalı
• İnternet bağlantısı gerekli

Kurulum Adımları:

1. Adım: Repository'yi klonlayın
git clone https://github.com/''' + owner + '''/''' + repo + '''

2. Adım: Proje dizinine girin
cd ''' + repo + '''

3. Adım: Bağımlılıkları yükleyin
Kullandığınız paket yöneticisine göre gerekli komutları çalıştırın.

4. Adım: Yapılandırma dosyasını düzenleyin
Kendi ihtiyaçlarınıza göre ayarları yapılandırın.

5. Adım: Projeyi çalıştırın
Artık ''' + name + '''\'ı kullanmaya başlayabilirsiniz!''' if content_type == 'github_repo' else '''
İpucu 1: Siteyi etkili kullanmak için ana menüyü keşfedin
Tüm özellikler ve bölümler açıkça organize edilmiş.

İpucu 2: Arama fonksiyonunu kullanın
Aradığınız içeriğe hızlıca ulaşabilirsiniz.

İpucu 3: Hesap oluşturun
Daha fazla özelliğe erişmek için ücretsiz hesap oluşturabilirsiniz.

İpucu 4: Mobil uygulamayı deneyin
Mobil cihazlarınızdan da rahatça erişebilirsiniz.

İpucu 5: Toplulukla etkileşime geçin
Forum ve sosyal medya kanallarını takip edin.'''}

[09:30-10:00] KAPANIŞ
Özetlersek, {name} {'projesi' if content_type == 'github_repo' else 'sitesi'}:
✓ Kolay kullanım ve {'entegrasyon' if content_type == 'github_repo' else 'erişim'}
✓ Yüksek performans {'ve güvenilirlik' if content_type != 'github_repo' else ''}
✓ {'Aktif topluluk desteği' if content_type == 'github_repo' else 'Zengin içerik'}
✓ {'Sürekli güncellemeler' if content_type == 'github_repo' else 'Kullanıcı dostu arayüz'}
✓ {'Kapsamlı dokümantasyon' if content_type == 'github_repo' else 'Faydalı kaynaklar'}

Bu {'proje' if content_type == 'github_repo' else 'site'}, {topics_str} alanlarında {'çalışıyorsanız' if content_type == 'github_repo' else 'ilgileniyorsanız'} kesinlikle {'denemenizi' if content_type == 'github_repo' else 'ziyaret etmenizi'} öneririm.

{('GitHub\'da ' + str(stars) + ' yıldız alan bu projeyi siz de kullanarak projelerinize değer katabilirsiniz.') if content_type == 'github_repo' and stars > 0 else 'Siz de kullanarak faydalanabilirsiniz.'}

Video işinize yaradıysa beğenmeyi ve abone olmayı unutmayın!
Yorumlarda sorularınızı bekliyorum.

Bir sonraki videoda görüşmek üzere! 👋
"""
