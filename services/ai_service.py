"""
AI Script Generation Service
Uses OpenAI or Anthropic to generate Turkish video scripts
"""

import os
from typing import Dict, Optional
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
    
    async def generate_turkish_script(self, content_data: Dict, style: str, video_duration: int = 10, custom_prompt: Optional[str] = None) -> str:
        """Generate Turkish video script based on duration
        
        Args:
            content_data: Content/repository data
            style: Video style (tutorial, review, quick_start)
            video_duration: Video duration in minutes (5, 10, or 15)
            custom_prompt: Optional custom instructions from user
        """
        
        if self.provider == "demo":
            return self._generate_demo_script(content_data, video_duration, custom_prompt)
        
        # Determine content type and build appropriate prompt
        content_type = content_data.get('type', 'github_repo')
        
        # Duration-specific configurations
        duration_configs = {
            5: {
                "word_range": "750-900",
                "flow": """Akış (doğal geçişlerle):
   İlk 20 saniye: Samimi bir giriş yap, projeyi tanıt
   1.5 dakika: Temel özelliklerini konuşarak açıkla
   2.5 dakika: En önemli 2-3 özelliği detaylandır
   1.5 dakika: Hızlı kullanım örneği göster
   30 saniye: Özet ve vedalaşma"""
            },
            10: {
                "word_range": "1500-1800",
                "flow": """Akış (doğal geçişlerle):
   İlk 30 saniye: Samimi bir giriş yap, projeyi tanıt, neler öğreneceklerini söyle
   1.5 dakika: Projeyi detaylı açıkla, arka planını anlat
   20 saniye: Doğal geçiş - "Şimdi özelliklere bakalım..."
   2.5 dakika: 3-4 ana özelliği konuşarak, doğal şekilde detaylandır
   20 saniye: Doğal geçiş - "Bunları pratikte nasıl kullanıyoruz?"
   2.5 dakika: Pratik kullanım örnekleri göster
   20 saniye: Doğal geçiş - "Şimdi kuruluma geçelim..."
   1 dakika: Kurulum adımlarını anlat
   30 saniye: Özet ve vedalaşma"""
            },
            15: {
                "word_range": "2250-2700",
                "flow": """Akış (doğal geçişlerle):
   İlk 30 saniye: Samimi bir giriş yap, projeyi tanıt
   2 dakika: Projeyi detaylı açıkla, arka plan bilgisi ver
   30 saniye: Doğal geçiş - "Gelin özelliklere bakalım..."
   3.5 dakika: 4-5 ana özelliği doğal konuşma akışıyla detaylandır
   30 saniye: Doğal geçiş - "Bunları pratikte görelim..."
   4 dakika: Kapsamlı kullanım örnekleri ve senaryolar
   30 saniye: Doğal geçiş - "Şimdi kurulum ve ileri konulara geçelim..."
   2 dakika: Detaylı kurulum ve optimizasyon ipuçları
   1 dakika: Topluluk, dokümantasyon ve kaynaklar
   30 saniye: Kapsamlı özet ve sonraki adımlar"""
            }
        }
        
        config = duration_configs.get(video_duration, duration_configs[10])
        
        if content_type == 'document':
            # Document-specific prompt
            title = content_data.get('title', 'Doküman')
            file_type = content_data.get('file_type', 'document')
            content = content_data.get('content', '')[:2000]
            headings = content_data.get('headings', [])
            headings_text = '\n'.join([f"- {h.get('text', '')}" for h in headings[:10]])
            word_count = content_data.get('word_count', 0)
            
            # Document flow - focus on content explanation
            doc_flow = config['flow'].replace('projeyi', 'dokümanı').replace('Projeyi', 'Dokümanı').replace('özelliklere', 'içeriğe').replace('kurulum', 'önemli noktalara')
            
            prompt = f"""
Yüklenmiş bir doküman hakkında {video_duration} dakikalık Türkçe eğitim videosu scripti oluştur.

Doküman Bilgileri:
- Başlık: {title}
- Dosya Tipi: {file_type.upper()}
- Kelime Sayısı: {word_count}

Ana Başlıklar/Bölümler:
{headings_text if headings_text else '(Başlık bulunamadı)'}

Doküman İçeriği:
{content}

Gereksinimler:
1. Toplam süre: Tam {video_duration} dakika (yaklaşık {config['word_range']} kelime)
2. Dil: Türkçe, profesyonel ama samimi
3. Stil: Eğitici ve açıklayıcı - dokümanın içeriğini anlat
4. Akış rehberi:
{doc_flow}

5. BÖLÜM BAŞLIKLARI KULLANMA - sadece doğal konuşma akışı
6. Timestamp veya [zaman] işaretleri kullanma
7. Dokümandaki konuları doğal geçişlerle birbirine bağla ("Şimdi...", "Gelin bakalım...", "Peki..." gibi)
8. Sanki birisiyle konuşuyormuş gibi samimi ve akıcı yaz
9. Teknik terimleri günlük dille açıkla
10. İzleyiciyle bağ kur - dokümanın önemli noktalarını vurgula ve örneklerle açıkla
11. Dokümanın içeriğini özetle ve öğretici bir şekilde sun - "web sitesi" veya "proje" deme, dokümanın kendisinden bahset
{f'''

ÖNEMLİ - KULLANICININ ÖZEL TALİMATLARI:
{custom_prompt}

Bu talimatları mutlaka dikkate al ve script'i buna göre hazırla!
''' if custom_prompt else ''}

Doğal, başlıksız ve akıcı scripti şimdi oluştur:
"""
        elif content_type == 'github_repo':
            # GitHub repository prompt
            prompt = f"""
GitHub projesi için {video_duration} dakikalık Türkçe eğitim videosu scripti oluştur.

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
1. Toplam süre: Tam {video_duration} dakika (yaklaşık {config['word_range']} kelime)
2. Dil: Türkçe, profesyonel ama samimi
3. Stil: {style} (tutorial/review/quick_start)
4. Akış rehberi:
{config['flow']}

5. BÖLÜM BAŞLIKLARI KULLANMA - sadece doğal konuşma akışı
6. Timestamp veya [zaman] işaretleri kullanma
7. Konuları doğal geçişlerle birbirine bağla ("Şimdi...", "Gelin bakalım...", "Peki..." gibi)
8. Sanki birisiyle konuşuyormuş gibi samimi ve akıcı yaz
9. Teknik terimleri günlük dille açıkla
10. İzleyiciyle bağ kur (sorular sor, örnekler ver, "siz de..." diye önerilerde bulun)
{f'''

ÖNEMLİ - KULLANICININ ÖZEL TALİMATLARI:
{custom_prompt}

Bu talimatları mutlaka dikkate al ve script'i buna göre hazırla!
''' if custom_prompt else ''}

Doğal, başlıksız ve akıcı scripti şimdi oluştur:
"""
        else:
            # General website prompt
            title = content_data.get('title', 'Web Sitesi')
            description = content_data.get('description', '')
            main_content = content_data.get('content', '')[:2000]
            headings = content_data.get('headings', [])
            headings_text = '\n'.join([f"- {h.get('text', '')}" for h in headings[:10]])
            
            # Use same flow structure for websites
            website_flow = config['flow'].replace('projeyi', 'siteyi').replace('Projeyi', 'Siteyi')
            
            prompt = f"""
Bir web sitesi hakkında {video_duration} dakikalık Türkçe eğitim/tanıtım videosu scripti oluştur.

Web Sitesi Bilgileri:
- Başlık: {title}
- URL: {content_data.get('url', '')}
- Açıklama: {description}

Ana Başlıklar:
{headings_text}

İçerik Özeti:
{main_content}

Gereksinimler:
1. Toplam süre: Tam {video_duration} dakika (yaklaşık {config['word_range']} kelime)
2. Dil: Türkçe, profesyonel ama samimi
3. Stil: {style} (tutorial/review/quick_start)
4. Akış rehberi:
{website_flow}

5. BÖLÜM BAŞLIKLARI KULLANMA - sadece doğal konuşma akışı
6. Timestamp veya [zaman] işaretleri kullanma
7. Konuları doğal geçişlerle birbirine bağla ("Şimdi...", "Gelin bakalım...", "Peki..." gibi)
8. Sanki birisiyle konuşuyormuş gibi samimi ve akıcı yaz
9. Teknik terimleri günlük dille açıkla
10. İzleyiciyle bağ kur (sorular sor, örnekler ver, "siz de..." diye önerilerde bulun)
{f'''

ÖNEMLİ - KULLANICININ ÖZEL TALİMATLARI:
{custom_prompt}

Bu talimatları mutlaka dikkate al ve script'i buna göre hazırla!
''' if custom_prompt else ''}

Doğal, başlıksız ve akıcı scripti şimdi oluştur:
"""
        
        if self.provider == "anthropic":
            # Claude'u öncelikli olarak kullan
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2500,
                temperature=0.7,
                system="Sen profesyonel Türkçe video scripti yazan bir AI asistanısın. Eğitici, samimi ve akıcı scriptler yazarsın.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            # Claude response'u düzgün şekilde al
            if response.content and len(response.content) > 0:
                text_content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
                return text_content
            return self._generate_demo_script(content_data, video_duration, custom_prompt)
            
        elif self.provider == "openai":
            # OpenAI'ı yedek olarak kullan
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
            return content if content else self._generate_demo_script(content_data, video_duration, custom_prompt)
        
        return self._generate_demo_script(content_data, video_duration, custom_prompt)
    
    def _generate_demo_script(self, content_data: Dict, video_duration: int = 10, custom_prompt: Optional[str] = None) -> str:
        """Generate demo script when no API key is available
        
        Args:
            content_data: Content/repository data
            video_duration: Video duration in minutes (5, 10, or 15)
            custom_prompt: Optional custom instructions from user
        """
        
        content_type = content_data.get('type', 'github_repo')
        is_github = content_type == 'github_repo'
        is_document = content_type == 'document'
        
        if is_document:
            # Document content
            name = content_data.get('title', 'Doküman')
            description = content_data.get('content', '')[:200] + '...' if len(content_data.get('content', '')) > 200 else content_data.get('content', 'Doküman içeriği')
            file_type = content_data.get('file_type', 'belge')
            word_count = content_data.get('word_count', 0)
            topics_str = f'{file_type.upper()} belgesi, {word_count} kelime'
            language = 'Doküman'
            stars = 0
            forks = 0
            license_info = 'N/A'
            owner = ''
            repo = ''
        elif is_github:
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
        
        # Prepare dynamic text parts to avoid f-string backslash issues
        content_label = 'projesini' if is_github else ('dokümanını' if is_document else 'sitesini')
        setup_verb = 'kurulur ve' if is_github else ''
        section_title = 'PROJE' if is_github else ('DOKÜMAN' if is_document else 'SİTE')
        
        github_stars_text = f"GitHub'da {stars} yıldız almış popüler bir açık kaynak projedir." if is_github and stars > 0 else ''
        forks_text = f"{forks} fork ile aktif bir geliştirici topluluğuna sahip." if is_github and forks > 0 else ''
        license_text = f"Proje {license_info} lisansı altında dağıtılıyor." if is_github and license_info != 'N/A' else ''
        
        content_type_label = 'projenin' if is_github else 'sitenin'
        api_or_ui = 'bir API' + chr(39) + 'ye' if is_github else 'bir arayüze'
        integration_text = 'Birkaç satır kod ile projenize entegre edebilirsiniz.' if is_github else 'Kullanıcı dostu tasarımı ile kolayca kullanabilirsiniz.'
        docs_text = 'Dokümantasyon oldukça kapsamlı ve örneklerle desteklenmiş.' if is_github else 'Her şey düzenli ve anlaşılır şekilde sunulmuş.'
        
        perf_label = 'Yüksek Performans' + (' ve Güvenilirlik' if not is_github else '')
        perf_text = 'Proje, optimize edilmiş kod yapısı sayesinde yüksek performans sağlıyor.' if is_github else 'Site, modern teknolojilerle hızlı ve güvenilir çalışıyor.'
        tech_text = f"{language} dilinin avantajlarından tam anlamıyla yararlanıyor." if is_github else 'Kullanıcı deneyimi her zaman öncelikli.'
        
        feature3_title = 'Geniş Topluluk Desteği' if is_github else 'Zengin İçerik'
        feature3_text = f"{forks} fork ve aktif bir geliştirici topluluğu." if is_github and forks > 0 else 'Çeşitli içerikler ve kaynaklar sunuyor.'
        
        demo_intro = 'canlı bir demo ile' if is_github else ''
        name_suffix1 = chr(39) + 'ın' if is_github else chr(39) + 'nin'
        
        demo_title = 'DEMO VE' if is_github else ''
        name_suffix2 = chr(39) + 'ı' if is_github else chr(39) + 'yi'
        
        action_desc = chr(39) + 'ı kendi projenize nasıl kuracağınızı' if is_github else chr(39) + 'den nasıl en iyi şekilde faydalanacağınızı'
        section3_title = 'KURULUM REHBERİ' if is_github else 'İPUÇLARI VE ÖNERİLER'
        action_verb = chr(39) + 'ı kurmak' if is_github else chr(39) + 'den en iyi şekilde yararlanmak'
        action_intro = 'Adım adım gidelim.' if is_github else 'İşte ipuçları:'
        
        if is_github:
            setup_section = f"""Öncelikle sisteminizde şu gereksinimlerin olduğundan emin olun:
• {language} kurulu olmalı
• Git kurulu olmalı
• İnternet bağlantısı gerekli

Kurulum Adımları:

1. Adım: Repository'yi klonlayın
git clone https://github.com/{owner}/{repo}

2. Adım: Proje dizinine girin
cd {repo}

3. Adım: Bağımlılıkları yükleyin
Kullandığınız paket yöneticisine göre gerekli komutları çalıştırın.

4. Adım: Yapılandırma dosyasını düzenleyin
Kendi ihtiyaçlarınıza göre ayarları yapılandırın.

5. Adım: Projeyi çalıştırın
Artık {name}{chr(39)}ı kullanmaya başlayabilirsiniz!"""
        else:
            setup_section = """
İpucu 1: Siteyi etkili kullanmak için ana menüyü keşfedin
Tüm özellikler ve bölümler açıkça organize edilmiş.

İpucu 2: Arama fonksiyonunu kullanın
Aradığınız içeriğe hızlıca ulaşabilirsiniz.

İpucu 3: Hesap oluşturun
Daha fazla özelliğe erişmek için ücretsiz hesap oluşturabilirsiniz.

İpucu 4: Mobil uygulamayı deneyin
Mobil cihazlarınızdan da rahatça erişebilirsiniz.

İpucu 5: Toplulukla etkileşime geçin
Forum ve sosyal medya kanallarını takip edin."""
        
        closing_label = 'projesi' if is_github else 'sitesi'
        closing_integration = 'entegrasyon' if is_github else 'erişim'
        closing_perf = 'Yüksek performans' + (' ve güvenilirlik' if not is_github else '')
        closing_feature3 = 'Aktif topluluk desteği' if is_github else 'Zengin içerik'
        closing_feature4 = 'Sürekli güncellemeler' if is_github else 'Kullanıcı dostu arayüz'
        closing_feature5 = 'Kapsamlı dokümantasyon' if is_github else 'Faydalı kaynaklar'
        
        closing_type = 'proje' if is_github else 'site'
        closing_context = 'çalışıyorsanız' if is_github else 'ilgileniyorsanız'
        closing_action = 'denemenizi' if is_github else 'ziyaret etmenizi'
        
        closing_final = f"GitHub'da {stars} yıldız alan bu projeyi siz de kullanarak projelerinize değer katabilirsiniz." if is_github and stars > 0 else 'Siz de kullanarak faydalanabilirsiniz.'
        
        # Build base demo script
        base_script = f"""[00:00-00:30] AÇILIŞ
Merhaba! Bugün {name} {content_label} detaylıca inceleyeceğiz. 
{description}

Bu videoda neler öğreneceksiniz?
✓ {name} nedir ve nasıl çalışır
✓ Ana özellikleri nelerdir
✓ Nasıl {setup_verb} kullanılır

Hadi başlayalım!

[00:30-02:00] {section_title} TANITIMI
{name}, {description}

{github_stars_text}

Bu {closing_type} özellikle şu alanlarda kullanılıyor:
• {topics_str}

{forks_text}
{license_text}

[02:00-02:20] GEÇİŞ 1
Şimdi bu {content_type_label} ana özelliklerine detaylı bir şekilde bakalım...

[02:20-05:00] ANA ÖZELLİKLER
Özellik 1: Kolay Kullanım ve Entegrasyon
{name} çok basit ve anlaşılır {api_or_ui} sahip. 
{integration_text}
{docs_text}

Özellik 2: {perf_label}
{perf_text}
{tech_text}

Özellik 3: {feature3_title}
{feature3_text}
Sorunlarınıza hızlı çözüm bulabilir, yeni özellikler önerebilirsiniz.

Özellik 4: Sürekli Güncellemeler
Proje düzenli olarak güncelleniyor ve yeni özellikler ekleniyor.
Güvenlik güncellemeleri hızlı bir şekilde yayınlanıyor.

[05:00-05:20] GEÇİŞ 2
Şimdi {demo_intro} {name}{name_suffix1} nasıl çalıştığını görelim...

[05:20-08:00] {demo_title} KULLANIM
Gerçek bir kullanım senaryosu üzerinden {name}{name_suffix2} inceleyelim.

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
Artık {name}{action_desc} görelim...

[08:20-09:30] {section3_title}
{name}{action_verb} oldukça basit. {action_intro}

{setup_section}

[09:30-10:00] KAPANIŞ
Özetlersek, {name} {closing_label}:
✓ Kolay kullanım ve {closing_integration}
✓ {closing_perf}
✓ {closing_feature3}
✓ {closing_feature4}
✓ {closing_feature5}

Bu {closing_type}, {topics_str} alanlarında {closing_context} kesinlikle {closing_action} öneririm.

{closing_final}

Video işinize yaradıysa beğenmeyi ve abone olmayı unutmayın!
Yorumlarda sorularınızı bekliyorum.

Bir sonraki videoda görüşmek üzere! 👋
"""
        
        # Add custom prompt note if provided
        if custom_prompt:
            return f"""[DEMO MODE] Bu demo script, gerçek AI API anahtarı olmadığı için kullanılıyor. 

KULLANICI TALİMATI: {custom_prompt}

NOT: Gerçek AI anahtarı eklediğinizde (OPENAI_API_KEY veya ANTHROPIC_API_KEY), bu talimat dikkate alınarak özelleştirilmiş script oluşturulacak.

---

{base_script}"""
        
        # Return normal demo script without custom prompt note
        return base_script
