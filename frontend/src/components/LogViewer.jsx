import React, { useEffect, useRef } from 'react';

export function LogViewer({ logs }) {
    const endRef = useRef(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    return (
        <div className="bg-muted/30 rounded-lg p-4 h-64 overflow-y-auto font-mono text-xs border border-border/50">
            {logs.length === 0 ? (
                <div className="text-muted-foreground italic text-center mt-20">Waiting for actions...</div>
            ) : (
                logs.map((log, i) => (
                    <div key={i} className="mb-1">
                        <span className="text-muted-foreground opacity-50">[{new Date().toLocaleTimeString()}]</span>{' '}
                        <span className={log.type === 'error' ? 'text-red-400' : 'text-foreground'}>
                            {log.message}
                        </span>
                        {log.details && (
                            <pre className="ml-4 mt-1 text-xs opacity-70 overflow-x-auto whitespace-pre-wrap">
                                {JSON.stringify(log.details, null, 2)}
                            </pre>
                        )}
                    </div>
                ))
            )}
            <div ref={endRef} />
        </div>
    );
}
