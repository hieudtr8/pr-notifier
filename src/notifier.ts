import axios from 'axios';

export class NotificationService {
  constructor(private ntfyTopic: string) {}

  async sendNotification(
    title: string,
    message: string,
    tags: string
  ): Promise<void> {
    try {
      await axios.post(`https://ntfy.sh/${this.ntfyTopic}`, message, {
        headers: {
          Title: title,
          Priority: 'high',
          Tags: tags,
          'Content-Type': 'text/plain; charset=utf-8',
        },
      });
      console.log(`✅ Notification sent successfully for: ${title}`);
    } catch (error) {
      console.error(`❌ Error sending notification: ${error}`);
    }
  }
}
