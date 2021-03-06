from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    abort
)
from flask_login import current_user, login_required
from flask_rq import get_queue
from app import db

import os
import datetime
import urllib
import logging
import html2text
import sys

import sqlalchemy
from sqlalchemy import create_engine, not_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import *


from .forms import RoomRequestForm, ActivityForm, TransferForm
from .helpers import get_room_request_from_form, get_form_from_room_request
from ..decorators import admin_required
from ..email import send_email, send_custom_email
from ..models import Activity, EditableHTML, RoomRequest, Guest, User, Role

logger = logging.getLogger('werkzeug')
room_request = Blueprint('room_request', __name__)

@room_request.route('/')
@login_required
def index():
    """View all room requests."""
    room_requests = RoomRequest.query.all()
    if (current_user.role.name == 'Administrator'):
        return render_template('admin/index.html', room_requests=room_requests)
    else:
        return render_template('staff/index.html', room_requests=room_requests)

@room_request.route('/<int:id>/manage')
@room_request.route('/<int:id>/patient')
@login_required
def manage(id):
    """Manage room request."""
    room_request = RoomRequest.query.get(id)
    if room_request is None:
        return abort(404)
    return render_template('room_request/manage.html', room_request=room_request)


@login_required
@room_request.route('/<int:id>/info')
def requester_info(id):
    """View patient info of given room request."""
    room_request = RoomRequest.query.get(id)
    if room_request is None:
        return abort(404)
    return render_template('room_request/manage.html', room_request=room_request)


@room_request.route('/<int:id>/room-occupancy')
@login_required
def room_occupancy_info(id):
    """View room occupancy needs for given room request."""
    room_request = RoomRequest.query.get(id)
    if room_request is None:
        return abort(404)
    return render_template('room_request/manage.html', room_request=room_request)


@room_request.route('/<int:id>/guests')
@login_required
def guest_info(id):
    """View table of guests for given room request."""
    room_request = RoomRequest.query.get(id)
    if room_request is None:
        return abort(404)
    return render_template('room_request/manage.html', room_request=room_request)

@room_request.route('/<int:id>/comments', methods=['GET', 'POST'])
@login_required
def comments(id):
    room_request = RoomRequest.query.get(id)
    if room_request is None:
        return abort(404)

    comments_all = Activity.query.filter_by(room_request_id=id)
    activity_form = ActivityForm()

    if activity_form.validate_on_submit():
        activity = Activity(
            text=activity_form.body.data,
            user_id=current_user.id,
            room_request_id=room_request.id)
        try:
            db.session.add(activity)
            db.session.commit()
            flash("Your comment has been added to the post", 'form-post')
        except:
            db.session.rollback()
        activity_form.body.data = ''

    return render_template('room_request/manage.html',
        id=id,
        room_request=room_request,
        activity_form=activity_form,
        comments_all=comments_all)

@room_request.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit room request info."""
    room_request = RoomRequest.query.get(id)
    if room_request is None:
        return abort(404)

    form = get_form_from_room_request(room_request)
    if form.validate_on_submit():
        room_request = get_room_request_from_form(form)
        try:
            db.session.add(room_request)
            db.session.commit()
            flash('Successfully saved changes.', 'form-success')
        except IntegrityError:
            db.session.rollback()
            flash('Unable to save changes. Please try again.', 'form-error')
    return render_template('room_request/manage.html', room_request=room_request, form=form)


@room_request.route('<int:id>/delete', methods=['GET', 'DELETE'])
@login_required
def delete(id):
    """Request deletion of a room request, but does not actually perform the action until user confirmation."""
    room_request = RoomRequest.query.get(id)
    if room_request is None:
        return abort(404)
    return render_template('room_request/manage.html', room_request=room_request)


@room_request.route('<int:id>/_delete', methods=['GET', 'DELETE'])
@login_required
def _delete(id):
    """Delete a room request."""
    room_request = RoomRequest.query.get(id)
    room_requests = RoomRequest.query.all()
    if room_request:
        db.session.delete(room_request)
        db.session.commit()
        # flash("Successfully deleted room request for " + room_request.first_name + " ", room_request.last_name + ".", 'success')
    if (current_user.role.name == 'Administrator'):
        return redirect(url_for('admin.index'))
    else:
        return redirect(url_for('staff.index'))


@room_request.route('/new', methods=['GET', 'POST'])
def new():
    """Room Request page."""
    editable_html_obj = EditableHTML.get_editable_html('form_instructions')
    editable_html_obj_email = EditableHTML.get_editable_html('email_confirmation')
    email = editable_html_obj_email.value
    form = RoomRequestForm(request.form)
    if form.validate_on_submit():
        try:
            room_request = get_room_request_from_form(form)
            db.session.add(room_request)
            db.session.commit()
            greeting = "<p>Dear " + room_request.last_name + " Family,</p>\n\n"
            info = ('''<p>Thank you for contacting us to request a room at the Philadelphia Ronald McDonald House.
            You have requested an arrival date of ''' + room_request.patient_check_in.strftime("%m/%d/%Y") +
            " and a departure date of " + room_request.patient_check_out.strftime("%m/%d/%Y") + ".</p>\n\n")
            email = greeting + info + email
            get_queue().enqueue(
                send_custom_email,
                recipient=room_request.email,
                subject='PRMH Room Request Submitted',
                custom_html=email
            )
            return render_template('room_request/success.html')
        except IntegrityError:
            db.session.rollback()
            flash('Unable to save changes. Please try again.', 'form-error')

    return render_template('room_request/new.html', form=form, editable_html_obj=editable_html_obj)


@room_request.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def view(id):
    room_request = RoomRequest.query.get(id)
    if room_request is None:
        return abort(404)

    comments = Activity.query.filter_by(room_request_id=id)
    activity_form = ActivityForm()
    transfer_form = TransferForm()

    if activity_form.validate_on_submit():
        activity = Activity(
            text=activity_form.body.data,
            user_id=current_user.id,
            room_request_id=room_request.id)
        try:
            db.session.add(activity)
            db.session.commit()
            flash("Your comment has been added to the post", 'form-post')
        except:
            db.session.rollback()
        activity_form.body.data = ''


    if transfer_form.validate_on_submit():
        flash("Succesfully transferred!")

    return render_template('room_request/manage.html',
        id=id,
        room_request=room_request,
        activity_form=activity_form,
        transfer_form=transfer_form,
        comments=comments)

def connectionString(table, dbString):
    return ("""SELECT ISNULL(
        (
         SELECT [sup{}].[{}ID]
         FROM [sup{}]
         WHERE [sup{}].[{}Desc] = {}
        ), 1)""".format(table, table, table, table, table, ("\'" + dbString.replace("'","''") + "\'")))

@room_request.route('/<int:id>/transfer', methods=['GET', 'POST'])
@login_required
def transfer(id):
    requestID = id
    room_request = RoomRequest.query.get(requestID)
    if room_request is None:
        return abort(404)
    con = 'Yes'
    transferred = False
    param_string = "DRIVER={};SERVER={};DATABASE={};UID={};PWD={};MARS_Connection={}".format(
            os.getenv('SQL_SERVER') or "{ODBC Driver 17 for SQL Server}",
            os.getenv('AZURE_SERVER'),
            os.getenv('AZURE_DATABASE'),
            os.getenv('AZURE_USERNAME'),
            os.getenv('AZURE_PASS'),
            con)
    params = urllib.parse.quote_plus(param_string) 
    engine = sqlalchemy.engine.create_engine("mssql+pyodbc:///?odbc_connect=%s" % params)
    session = sessionmaker(bind=engine)()
    metadata = MetaData(bind=engine)

    family = Table('Family', metadata, autoload=True)
    familyMember = Table('FamilyMember', metadata, autoload=True)
    familyWaitList = Table('FamilyWaitList', metadata, autoload=True)
    familyWaitListMember = Table('FamilyWaitListMember', metadata, autoload=True)
    supRelationship = Table('supRelationship', metadata, autoload=True)
    supHospital = Table('supHospital', metadata, autoload=True)
    supWard = Table('supWard', metadata, autoload=True)
    supDiagnosis = Table('supDiagnosis', metadata, autoload=True)
    supReasonForVisit = Table('supReasonForVisit', metadata, autoload=True)
    supLanguage = Table('supLanguage', metadata, autoload=True)
    
    wheelchair = 0
    if room_request.wheelchair_access:
        wheelchair = 1

    #Is family new? 
    stayedBefore = room_request.previous_stay
    conn = engine.connect()

    primaryLangID = session.query(supLanguage).filter_by(LanguageDesc=room_request.primary_language)
    if primaryLangID.first() is None:
        primaryLangID = 1
    else:
        primaryLangID = primaryLangID.first()[0]

    secondaryLangID = session.query(supLanguage).filter_by(LanguageDesc=room_request.secondary_language)
    if secondaryLangID.first() is None:
        secondaryLangID = 1
    else:
        secondaryLangID = secondaryLangID.first()[0]
    
    if stayedBefore:
        famID = -1
        selectNames = family.select()
        result = conn.execute(selectNames)
        for row in result:
            #family found existing
            if row['PatientSurname'] == room_request.patient_last_name and row['PatientFirstName'] == room_request.patient_first_name:
                famID = row['FamilyID']
                break
        #family not found, create new record
        if famID < 0:
            try:
                insFam = family.insert().values(PatientSurname= room_request.patient_last_name, PatientFirstName= room_request.patient_first_name, PatientGender= room_request.patient_gender[0], PatientBirthDate = room_request.patient_dob, Address = (room_request.address_line_one + " " + room_request.address_line_two), City = room_request.city, ProvinceCode = room_request.state[0:3], PostalCode = room_request.zip_code, Country = room_request.country, Phone1Desc = "Phone 1", Phone1 = room_request.primary_phone, Phone2Desc = "Phone 2", Phone2 = room_request.secondary_phone, Phone3Desc = "", Phone3 = "", Phone4Desc = "", Phone4 = "", EmailAddress = "",  EmailAddress2 = "", DateCreated = room_request.created_at, CreatedBy = "Web Form", DateModified = room_request.created_at, ModifiedBy = "Web Form", PrimaryLanguageID=primaryLangID, SecondaryLanguageID=secondaryLangID, PatientRequiresWheelchair = wheelchair)
                famResult = conn.execute(insFam)
                famEntry = family.select().execute().fetchall()
                famID = famEntry[len(famEntry)-1].FamilyID
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)
                session.rollback()
                return render_template('room_request/transfer.html', id=id, transferred=transferred, error=e)
    #create new family record
    else: 
        try:
            insFam = family.insert().values(PatientSurname= room_request.patient_last_name, PatientFirstName= room_request.patient_first_name, PatientGender= room_request.patient_gender[0], PatientBirthDate = room_request.patient_dob, Address = (room_request.address_line_one + " " + room_request.address_line_two), City = room_request.city, ProvinceCode = room_request.state[0:3], PostalCode = room_request.zip_code, Country = room_request.country, Phone1Desc = "Phone 1", Phone1 = room_request.primary_phone, Phone2Desc = "Phone 2", Phone2 = room_request.secondary_phone, Phone3Desc = "", Phone3 = "", Phone4Desc = "", Phone4 = "", EmailAddress = "",  EmailAddress2 = "", DateCreated = room_request.created_at, CreatedBy = "Web Form", DateModified = room_request.created_at, ModifiedBy = "Web Form", PrimaryLanguageID=primaryLangID, SecondaryLanguageID=secondaryLangID,  PatientRequiresWheelchair = wheelchair)
            famResult = conn.execute(insFam)
            famEntry = family.select().execute().fetchall()
            famID = famEntry[len(famEntry)-1].FamilyID
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            session.rollback()
            return render_template('room_request/transfer.html', id=id, transferred=transferred, error=e)
    
    #check for existing family 
    existingFamMembers = []
    #select all family members from table
    familyMemberList = familyMember.select()
    famMemberListResult = conn.execute(familyMemberList)
    #for all of the family members found, add hem to existingFamlist
    for row in famMemberListResult:
        if row['FamilyID'] == famID:
            existingFamMembers.append(row)
    famMemberIDs = []
    #iterate over guests
    for guest in room_request.guests:
        found = False
        guard = 0
        if guest.guardian:
            guard = 1
        lastName = str(guest.name.split(' ')[1])
        firstName = str(guest.name.split(' ')[0])
        #if a guest eixsits, add their id to the list
        for existingMember in existingFamMembers:
            if existingMember['Surname'] == lastName and existingMember['FirstName'] == firstName:
                found = True
                famMemberIDs.append(existingMember['FamilyMemberID'])
            #else instert new members to FamilyMember    
        if not found:
            try: 
                lastName = str(guest.name.split(' ')[1])
                firstName = str(guest.name.split(' ')[0])
                relationshipID = session.query(supRelationship).filter_by(RelationshipDesc=guest.relationship_to_patient)
                if relationshipID.first() is None:
                    relationshipID = 1
                else:
                    relationshipID = relationshipID.first()[0]
                insFamMember = familyMember.insert().values(FamilyID = famID, Surname = lastName, FirstName = firstName, MiddleNames = '', BirthDate = guest.dob, Gender = '', RelationshipID = relationshipID, DateCreated = room_request.created_at, CreatedBy = 'Web Form', DateModified = room_request.created_at, ModifiedBy = 'Web Form', Notes = '', FirstCaregiver = guard)
                conn.execute(insFamMember)
                famMemberEntry = familyMember.select().execute().fetchall()
                famMemberID = famMemberEntry[len(famMemberEntry)-1].FamilyMemberID
                famMemberIDs.append(famMemberID)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)
                session.rollback()
                return render_template('room_request/transfer.html', id=id, transferred=transferred, error=e)
    #create waitlist reocrd
    try:
        hospitalID = session.query(supHospital).filter_by(HospitalDesc=room_request.patient_hospital)
        if hospitalID.first() is None:
            hospitalID = 1
        else:
            hospitalID = hospitalID.first()[0]
        wardID = session.query(supWard).filter_by(WardDesc=room_request.patient_hospital_department)
        if wardID.first() is None:
            wardID = 1
        else:
            wardID = wardID.first()[0]
        reasonForVisitID = session.query(supReasonForVisit).filter_by(ReasonForVisitDesc=room_request.patient_treatment_description)
        if reasonForVisitID.first() is None:
            reasonForVisitID = 1
        else:
            reasonForVisitID = reasonForVisitID.first()[0]
        DiagnosisID = session.query(supDiagnosis).filter_by(DiagnosisDesc=room_request.patient_diagnosis)
        if DiagnosisID.first() is None:
            DiagnosisID = 1
        else:
            DiagnosisID = DiagnosisID.first()[0]
        estimatedLengthOfStay = room_request.patient_check_in - room_request.patient_check_out
        otherReq = ''
        if room_request.full_bathroom:
            otherReq += "Full bathroom requested. "
        if room_request.pack_n_play:
            otherReq += "Pack n play requested. "
        insFamWaitList = familyWaitList.insert().values(FamilyID = famID, StartDate = room_request.patient_check_in, EndDate = room_request.patient_check_out, EndReasonID = 1, DiagnosisID = DiagnosisID, WardID = wardID, TentativeRoomID = 6, EstimatedLengthOfStay = estimatedLengthOfStay.days, ReferralName = '', ReferralOrganization = '', ReferralPhone1Desc = '', ReferralPhone1 = '', ReferralPhone1Ext = '', ReferralPhone2Desc = '', ReferralPhone2 = '', ReferralPhone2Ext = '', ReminderToConfirmGiven = 0, AskedAboutDiseaseSymptoms = 0, OutsideAgencyName = '', OutsideAgencyAddress = '', OutsideAgencyCity = '', OutsideAgencyProvinceCode = '', OutsideAgencyPostalCode = '', OutsideAgencyCountry = '', OutsideAgencyPhone1Desc = '', OutsideAgencyPhone1 = '', OutsideAgencyPhone2Desc = '', OutsideAgencyPhone2 = '', DateCreated = room_request.created_at, CreatedBy = 'Web Form', DateModified = room_request.created_at, ModifiedBy = 'Web Form', DateRequested = room_request.created_at, OtherSpecialRequests = otherReq, HospitalID = hospitalID)
        famWaitListResult = conn.execute(insFamWaitList)
        famWaitEntry = familyWaitList.select().execute().fetchall()
        waitlistID = famWaitEntry[len(famWaitEntry)-1].WaitListID
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        session.rollback()
        return render_template('room_request/transfer.html', id=id, transferred=transferred, error=e)
    #add family members to family waitlist
    try: 
        for member in famMemberIDs:
            print("Waitlist ID: "  + str(waitlistID) + " Family MemberID: " + str(member))
            insFamWaitListMember = familyWaitListMember.insert().values(WaitListID= waitlistID, FamilyMemberID=member, WillCheckIn=0)
            famWaitListMemberResult = conn.execute(insFamWaitListMember)    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        session.rollback()
        return render_template('room_request/transfer.html', id=id, transferred=transferred, error=e)


    db.session.delete(room_request)
    db.session.commit()
    flash(f'Successfully transfered room request for {room_request.first_name} {room_request.last_name}.', 'success')
    return redirect(url_for('admin.index'))


@room_request.route('/<int:id>/duplicates', methods=['GET', 'POST'])
@login_required
def duplicate_room_requests(id):
    room_request = RoomRequest.query.get(id)
    if room_request is None:
        return abort(404)
    # Duplicate room request must have:
    # (1) The same patient name
    # (2) A matching phone number or email for the requester
    duplicate_room_requests = RoomRequest.query \
        .filter_by(patient_first_name=room_request.patient_first_name, patient_last_name=room_request.patient_last_name) \
        .filter(or_(
            RoomRequest.primary_phone == room_request.primary_phone,
            RoomRequest.email == room_request.email,
        )) \
        .filter(RoomRequest.id != room_request.id) \
        .all()
    return render_template('room_request/duplicates.html', duplicate_room_requests=duplicate_room_requests)
