import ChatWindow from '@/components/ChatWindow';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Chat - CyberAI Assessment Platform',
  description: 'AI-powered compliance assessment and intelligent chat platform.',
};

const Home = () => {
  return <ChatWindow />;
};

export default Home;
