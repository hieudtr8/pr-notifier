import axios, { AxiosRequestConfig } from 'axios';
import * as https from 'https';
import { Config } from './types.js';

export class NotificationService {
  private config: Config;
  
  constructor(private ntfyTopic: string, config: Config) {
    this.config = config;
  }

  private async sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async sendNotification(
    title: string,
    message: string,
    tags: string,
    maxRetries: number = 3
  ): Promise<void> {
    let lastError: any;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        console.log(`📡 Sending notification (attempt ${attempt}/${maxRetries}): ${title}`);
        
        const axiosConfig: AxiosRequestConfig = {
          headers: {
            Title: title,
            Priority: 'high',
            Tags: tags,
            'Content-Type': 'text/plain; charset=utf-8',
            'User-Agent': 'pr-notifier/1.0.0',
          },
          timeout: 8000, // 8 second timeout
          validateStatus: () => true, // Accept any status code
        };

        // Add proxy configuration if available
        if (this.config.httpProxy || this.config.httpsProxy) {
          axiosConfig.proxy = false; // Disable axios default proxy detection
          if (this.config.httpsProxy) {
            const proxyUrl = new URL(this.config.httpsProxy);
            axiosConfig.proxy = {
              protocol: proxyUrl.protocol,
              host: proxyUrl.hostname,
              port: parseInt(proxyUrl.port) || (proxyUrl.protocol === 'https:' ? 443 : 80),
            };
          }
        }

        // Add SSL configuration and force IPv4
        axiosConfig.httpsAgent = new https.Agent({
          rejectUnauthorized: this.config.insecureSSL ? false : true,
          family: 4, // Force IPv4 to avoid IPv6 connection issues
        });

        const response = await axios.post(`https://ntfy.sh/${this.ntfyTopic}`, message, axiosConfig);
        
        if (response.status >= 200 && response.status < 300) {
          console.log(`✅ Notification sent successfully for: ${title} (status: ${response.status})`);
          return;
        } else {
          throw new Error(`HTTP ${response.status}: ${JSON.stringify(response.data)}`);
        }
      } catch (error) {
        lastError = error;
        
        if (axios.isAxiosError(error)) {
          console.error(`❌ Attempt ${attempt} failed - ${error.code}: ${error.message}`);
          if (error.response) {
            console.error(`   Response status: ${error.response.status}, data: ${JSON.stringify(error.response.data)}`);
          }
          if (error.request && !error.response) {
            console.error(`   Request made but no response received. Request timeout or network error.`);
            console.error(`   Request details: ${error.request.method} ${error.request.path}`);
          }
        } else {
          console.error(`❌ Attempt ${attempt} failed - Unexpected error: ${error}`);
        }
        
        if (attempt < maxRetries) {
          const delay = Math.pow(2, attempt - 1) * 1000; // Exponential backoff: 1s, 2s, 4s
          console.log(`🔄 Retrying in ${delay/1000}s...`);
          await this.sleep(delay);
        }
      }
    }
    
    console.error(`❌ All ${maxRetries} attempts failed. Last error:`, lastError);
  }
}
