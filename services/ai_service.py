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
    
    async def generate_turkish_script(self, repo_data: Dict, style: str) -> str:
        """Generate a 10-minute Turkish video script"""
        
        if self.provider == "demo":
            return self._generate_demo_script(repo_data)
        
        prompt = f"""
GitHub projesi için 10 dakikalık Türkçe eğitim videosu scripti oluştur.

Proje Bilgileri:
- İsim: {repo_data['name']}
- Açıklama: {repo_data['description']}
- Programlama Dili: {repo_data['language']}
- Yıldız Sayısı: {repo_data['stars']}
- Fork Sayısı: {repo_data['forks']}
- Konular: {', '.join(repo_data['topics'][:5])}
- Lisans: {repo_data['license']}

README Özeti:
{repo_data['readme'][:1500]}

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
            return content if content else self._generate_demo_script(repo_data)
        
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
            return self._generate_demo_script(repo_data)
        
        return self._generate_demo_script(repo_data)
    
    def _generate_demo_script(self, repo_data: Dict) -> str:
        """Generate demo script when no API key is available"""
        
        topics_str = ', '.join(repo_data['topics'][:3]) if repo_data['topics'] else 'web geliştirme, API entegrasyonu'
        
        return f"""[00:00-00:30] AÇILIŞ
Merhaba! Bugün {repo_data['name']} projesini detaylıca inceleyeceğiz. 
{repo_data['description']}

Bu videoda neler öğreneceksiniz?
✓ {repo_data['name']} nedir ve nasıl çalışır
✓ Ana özellikleri nelerdir
✓ Nasıl kurulur ve kullanılır

Hadi başlayalım!

[00:30-02:00] PROJE TANITIMI
{repo_data['name']}, {repo_data['language']} programlama diliyle geliştirilmiş, 
GitHub'da {repo_data['stars']} yıldız almış popüler bir açık kaynak projedir.

Proje, {repo_data['description']} amacıyla oluşturulmuş.

Bu proje özellikle şu alanlarda kullanılıyor:
• {topics_str}

{repo_data['forks']} fork ile aktif bir geliştirici topluluğuna sahip.
Proje {repo_data['license']} lisansı altında dağıtılıyor.

[02:00-02:20] GEÇİŞ 1
Şimdi bu projenin ana özelliklerine detaylı bir şekilde bakalım...

[02:20-05:00] ANA ÖZELLİKLER
Özellik 1: Kolay Kullanım ve Entegrasyon
{repo_data['name']} çok basit ve anlaşılır bir API'ye sahip. 
Birkaç satır kod ile projenize entegre edebilirsiniz.
Dokümantasyon oldukça kapsamlı ve örneklerle desteklenmiş.

Özellik 2: Yüksek Performans
Proje, optimize edilmiş kod yapısı sayesinde yüksek performans sağlıyor.
{repo_data['language']} dilinin avantajlarından tam anlamıyla yararlanıyor.

Özellik 3: Geniş Topluluk Desteği
{repo_data['forks']} fork ve aktif bir geliştirici topluluğu.
Sorunlarınıza hızlı çözüm bulabilir, yeni özellikler önerebilirsiniz.

Özellik 4: Sürekli Güncellemeler
Proje düzenli olarak güncelleniyor ve yeni özellikler ekleniyor.
Güvenlik güncellemeleri hızlı bir şekilde yayınlanıyor.

[05:00-05:20] GEÇİŞ 2
Şimdi canlı bir demo ile {repo_data['name']}'ın nasıl çalıştığını görelim...

[05:20-08:00] DEMO VE KULLANIM
Gerçek bir kullanım senaryosu üzerinden {repo_data['name']}'ı inceleyelim.

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
Artık {repo_data['name']}'ı kendi projenize nasıl kuracağınızı görelim...

[08:20-09:30] KURULUM REHBERİ
{repo_data['name']}'ı kurmak oldukça basit. Adım adım gidelim.

Öncelikle sisteminizde şu gereksinimlerin olduğundan emin olun:
• {repo_data['language']} kurulu olmalı
• Git kurulu olmalı
• İnternet bağlantısı gerekli

Kurulum Adımları:

1. Adım: Repository'yi klonlayın
git clone https://github.com/{repo_data['owner']}/{repo_data['repo']}

2. Adım: Proje dizinine girin
cd {repo_data['repo']}

3. Adım: Bağımlılıkları yükleyin
Kullandığınız paket yöneticisine göre gerekli komutları çalıştırın.

4. Adım: Yapılandırma dosyasını düzenleyin
Kendi ihtiyaçlarınıza göre ayarları yapılandırın.

5. Adım: Projeyi çalıştırın
Artık {repo_data['name']}'ı kullanmaya başlayabilirsiniz!

[09:30-10:00] KAPANIŞ
Özetlersek, {repo_data['name']} projesi:
✓ Kolay kullanım ve entegrasyon
✓ Yüksek performans
✓ Aktif topluluk desteği
✓ Sürekli güncellemeler
✓ Kapsamlı dokümantasyon

Bu proje, {topics_str} alanlarında çalışıyorsanız kesinlikle denemenizi öneririm.

GitHub'da {repo_data['stars']} yıldız alan bu projeyi siz de kullanarak projelerinize değer katabilirsiniz.

Video işinize yaradıysa beğenmeyi ve abone olmayı unutmayın!
Yorumlarda sorularınızı bekliyorum.

Bir sonraki videoda görüşmek üzere! 👋
"""
