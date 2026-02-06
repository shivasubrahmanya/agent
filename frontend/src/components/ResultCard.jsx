import React from 'react';
import { Building2, MapPin, Users, Globe, UserCheck, Mail, Phone, Linkedin, CheckCircle2, XCircle } from 'lucide-react';

export function ResultCard({ data }) {
    if (!data) return null;

    const { company, people, contacts, status, confidence_score, summary } = data;

    const isVerified = status === 'verified';

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">

            {/* Header / Status */}
            <div className={`p-6 rounded-xl border ${isVerified ? 'bg-green-500/10 border-green-500/20' : 'bg-destructive/10 border-destructive/20'}`}>
                <div className="flex items-start justify-between">
                    <div>
                        <h2 className="text-2xl font-bold flex items-center gap-2">
                            {company?.name || 'Unknown Company'}
                            {isVerified ? <CheckCircle2 className="text-green-500" /> : <XCircle className="text-destructive" />}
                        </h2>
                        <p className="text-muted-foreground mt-1">{summary || 'Analysis complete.'}</p>
                    </div>
                    <div className="text-right">
                        <div className="text-3xl font-bold">{(confidence_score * 100).toFixed(0)}%</div>
                        <div className="text-xs uppercase tracking-wider opacity-70">Confidence</div>
                    </div>
                </div>


                {/* Growth Signals */}
                {company?.growth_signals && company.growth_signals.length > 0 && (
                    <div className="mt-6 pt-4 border-t border-border/10">
                        <div className="flex flex-wrap gap-2">
                            {company.growth_signals.map((signal, i) => (
                                <span key={i} className="px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                                    🚀 {signal}
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* Company Details */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-border/10">
                    <div className="flex items-center gap-2">
                        <Building2 size={16} className="text-primary" />
                        <span className="text-sm">{company?.industry || 'N/A'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <MapPin size={16} className="text-primary" />
                        <span className="text-sm">{company?.location || 'N/A'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Users size={16} className="text-primary" />
                        <span className="text-sm">{company?.size || 'N/A'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Globe size={16} className="text-primary" />
                        <a href={company?.website} target="_blank" rel="noreferrer" className="text-sm hover:underline truncate max-w-[150px]">
                            {company?.website || 'N/A'}
                        </a>
                    </div>
                </div>

                {/* Recommended Action Banner */}
                {data.recommended_action && (
                    <div className="mt-6 p-3 bg-primary/10 border border-primary/20 rounded-lg flex items-center gap-3 text-primary text-sm font-medium">
                        <div className="p-1 bg-primary text-primary-foreground rounded">
                            <CheckCircle2 size={14} />
                        </div>
                        {data.recommended_action}
                    </div>
                )}
            </div>

            {/* Contacts Table */}
            {contacts && contacts.length > 0 && (
                <div className="bg-card rounded-xl border border-border overflow-hidden">
                    <div className="p-4 border-b border-border bg-muted/20">
                        <h3 className="font-semibold flex items-center gap-2">
                            <UserCheck size={18} /> Verified Contacts
                        </h3>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-border bg-muted/10">
                                    <th className="py-3 px-4 text-left font-medium text-muted-foreground">Name</th>
                                    <th className="py-3 px-4 text-left font-medium text-muted-foreground">Title</th>
                                    <th className="py-3 px-4 text-left font-medium text-muted-foreground">Email</th>
                                    <th className="py-3 px-4 text-left font-medium text-muted-foreground">Phone</th>
                                    <th className="py-3 px-4 text-right font-medium text-muted-foreground">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {contacts.map((contact, i) => (
                                    <tr key={i} className="border-b border-border hover:bg-muted/10 transition-colors">
                                        <td className="py-3 px-4 font-medium">
                                            {contact.linkedin_url ? (
                                                <a href={contact.linkedin_url} target="_blank" rel="noreferrer" className="hover:text-primary hover:underline flex items-center gap-1 group">
                                                    {contact.first_name} {contact.last_name}
                                                    <span className="opacity-0 group-hover:opacity-100 text-muted-foreground transition-opacity">
                                                        <Linkedin size={12} />
                                                    </span>
                                                </a>
                                            ) : (
                                                <span>{contact.first_name} {contact.last_name}</span>
                                            )}
                                        </td>
                                        <td className="py-3 px-4 text-muted-foreground">{contact.title}</td>
                                        <td className="py-3 px-4">
                                            {contact.email ? (
                                                <a href={`mailto:${contact.email}`} className="flex items-center gap-2 text-green-400 hover:text-green-300 hover:underline">
                                                    <Mail size={14} />
                                                    {contact.email}
                                                </a>
                                            ) : (
                                                <span className="opacity-30">-</span>
                                            )}
                                        </td>
                                        <td className="py-3 px-4">
                                            {contact.phone ? (
                                                <div className="flex items-center gap-2">
                                                    <Phone size={14} className="text-muted-foreground" />
                                                    {contact.phone}
                                                </div>
                                            ) : (
                                                <span className="opacity-30">-</span>
                                            )}
                                        </td>
                                        <td className="py-3 px-4 text-right">
                                            {contact.linkedin_url && (
                                                <a href={contact.linkedin_url} target="_blank" rel="noreferrer" className="inline-flex p-1.5 hover:bg-blue-500/20 text-blue-400 rounded-md transition-colors">
                                                    <Linkedin size={16} />
                                                </a>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* People Found (if no contacts) */}
            {(!contacts || contacts.length === 0) && people && people.length > 0 && (
                <div className="bg-card rounded-xl border border-border p-6">
                    <h3 className="font-semibold mb-4">People Found</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {people.slice(0, 6).map((p, i) => (
                            <div key={i} className="p-3 bg-muted/20 rounded-lg flex justify-between items-start">
                                <div>
                                    {p.linkedin_url ? (
                                        <a href={p.linkedin_url} target="_blank" rel="noreferrer" className="font-medium hover:text-primary hover:underline flex items-center gap-1 group">
                                            {p.name}
                                            <span className="opacity-0 group-hover:opacity-100 text-muted-foreground transition-opacity">
                                                <Linkedin size={10} />
                                            </span>
                                        </a>
                                    ) : (
                                        <div className="font-medium">{p.name}</div>
                                    )}
                                    <div className="text-xs text-muted-foreground">{p.title}</div>
                                </div>
                                <div className="text-xs px-2 py-1 rounded bg-background border border-border">
                                    Power: {p.decision_power}/10
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
