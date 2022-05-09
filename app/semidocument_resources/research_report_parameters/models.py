"""
Models for "research report parameters" package.
"""
from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.semidocument_resources.research_reports.models import ResearchReport


# association table for many-to-many research report and report parameters
reportparameters = db.Table(
    'reportparameters',
    db.Column('report_id', db.BigInteger, db.ForeignKey(
        'research_report.id', name='reportparameters_report_id_fkey',
        ondelete="CASCADE"), nullable=False),
    db.Column('parameter_id', db.Integer, db.ForeignKey(
        'research_report_parameter.id',
        name='reportparameters_parameter_id_fkey', ondelete="CASCADE"),
              nullable=False),
    UniqueConstraint('report_id', 'parameter_id',
                     name='ac_report_id_parameter_id_key'),
)


class ResearchReportParameter(BaseModel):

    __tablename__ = 'research_report_parameter'

    parameter_name = db.Column(db.String(256), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'),
                           nullable=False)
    weightage = db.Column(db.String(32))
    description = db.Column(db.String)
    edited_description = db.Column(db.String)
    sequence = db.Column(db.Integer)

    # relationships
    research_reports = db.relationship(
        'ResearchReport', secondary=reportparameters, backref=db.backref(
            'parameters', lazy='dynamic',
            order_by="ResearchReportParameter.sequence"), passive_deletes=True)
    account = db.relationship('Account', backref=db.backref(
        'research_report_parameters'))

    def __init__(self,  *args, **kwargs):
        super(ResearchReportParameter, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ResearchReportParameter %r>' % (self.parameter_name)
