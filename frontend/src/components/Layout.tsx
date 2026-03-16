import React from 'react';

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
}

const Layout: React.FC<LayoutProps> = ({ children, title = 'TDM System' }) => {
  return (
    <div>
      <header >
        <div >
          <h1 >{title}</h1>
          <p >Terrorism Detection & Monitoring System</p>
        </div>
      </header>
      
      <main>
        {children}
      </main>
      
      <footer>
      </footer>
    </div>
  );
};

export default Layout;