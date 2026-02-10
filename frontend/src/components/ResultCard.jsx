import React from 'react';
import { Building2, MapPin, Users, Globe, UserCheck, Mail, Phone, Linkedin, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

export function ResultCard({ data }) {
    if (!data) return null;

    const { company, people, contacts, status, confidence_score, summary, apollo_error, snov_error } = data;

    const isVerified = status === 'verified';

    // Helper to render a contact row
    const ContactRow = ({ contact }) => (
        <tr className="border-b border-border hover:bg-muted/10 transition-colors">
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
            <td className="py-3 px-4 text-right">
                {contact.linkedin_url && (
                    <a href={contact.linkedin_url} target="_blank" rel="noreferrer" className="inline-flex p-1.5 hover:bg-blue-500/20 text-blue-400 rounded-md transition-colors">
                        <Linkedin size={16} />
                    </a>
                )}
            </td>
        </tr>
    );

    // Section Component
    const ContactSection = ({ title, sourceContacts, error, iconColor, badgeColor }) => (
        <div className="bg-card rounded-xl border border-border overflow-hidden mb-6">
            <div className="p-4 border-b border-border bg-muted/20 flex justify-between items-center">
                <h3 className="font-semibold flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${iconColor}`} />
                    {title} <span className="text-muted-foreground font-normal text-xs">({sourceContacts?.length || 0})</span>
                </h3>
                {error && (
                    <div className="flex items-center gap-2 text-xs text-destructive bg-destructive/10 px-2 py-1 rounded border border-destructive/20">
                        <AlertTriangle size={12} />
                        {error}
                    </div>
                )}
            </div>

            <div className="overflow-x-auto">
                {sourceContacts && sourceContacts.length > 0 ? (
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border bg-muted/10">
                                <th className="py-3 px-4 text-left font-medium text-muted-foreground">Name</th>
                                <th className="py-3 px-4 text-left font-medium text-muted-foreground">Title</th>
                                <th className="py-3 px-4 text-left font-medium text-muted-foreground">Email</th>
                                <th className="py-3 px-4 text-right font-medium text-muted-foreground">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sourceContacts.map((c, i) => <ContactRow key={i} contact={c} />)}
                        </tbody>
                    </table>
                ) : (
                    <div className="p-8 text-center text-muted-foreground text-sm">
                        {error ? (
                            <div className="flex flex-col items-center gap-2">
                                <p>Unable to fetch data from {title}.</p>
                                <p className="text-xs opacity-70">Error: {error}</p>
                            </div>
                        ) : (
                            "No contacts found from this source."
                        )}
                    </div>
                )}
            </div>
        </div>
    );

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
            </div>

            {/* Apollo Section */}
            <ContactSection
                title="Apollo.io Results"
                sourceContacts={data.apollo_contacts}
                error={apollo_error}
                iconColor="bg-blue-500"
            />

            {/* Snov.io Section */}
            <ContactSection
                title="Snov.io Results"
                sourceContacts={data.snov_contacts}
                error={snov_error}
                iconColor="bg-purple-500"
            />

            {/* All Identified People (General) */}
            {people && people.length > 0 && (
                <div className="bg-card rounded-xl border border-border p-6">
                    <h3 className="font-semibold mb-4 text-sm uppercase tracking-wider text-muted-foreground">General Decision Makers</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {people.slice(0, 8).map((p, i) => (
                            <div key={i} className="p-3 bg-muted/20 rounded-lg flex justify-between items-start">
                                <div>
                                    <div className="font-medium text-sm flex items-center gap-1.5">
                                        {p.linkedin_url ? (
                                            <a href={p.linkedin_url} target="_blank" rel="noreferrer" className="hover:text-primary hover:underline flex items-center gap-1 group">
                                                {p.name}
                                                <Linkedin size={10} className="text-muted-foreground group-hover:text-primary" />
                                            </a>
                                        ) : (
                                            p.name
                                        )}
                                    </div>
                                    <div className="text-xs text-muted-foreground">{p.title}</div>
                                </div>
                                <div className="text-[10px] px-1.5 py-0.5 rounded bg-background border border-border">
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
