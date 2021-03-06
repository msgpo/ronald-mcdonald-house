from ..models import RoomRequest, Guest
from .forms import RoomRequestForm

def get_room_request_from_form(form):
    """Returns a room request from the given submitted RoomRequestForm."""
    room_request = RoomRequest(
        first_name=form.first_name.data,
        last_name=form.last_name.data,
        relationship_to_patient=form.rel_to_patient.data,
        address_line_one=form.street_address.data,
        address_line_two=form.apt_st_address.data,
        city=form.city.data,
        state=form.state.data,
        zip_code=form.zipcode.data,
        country=form.country.data,
        primary_phone=form.phone_number.data,
        secondary_phone=form.alt_phone_number.data,
        email=form.email.data,
        primary_language=form.primary_language.data,
        secondary_language=form.secondary_language.data,
        previous_stay=form.stayed_before.data,
        patient_first_name=form.patient_first_name.data,
        patient_last_name=form.patient_last_name.data,
        patient_dob=form.patient_dob.data,
        patient_gender=form.patient_gender.data,
        patient_hospital=form.hospital.data,
        patient_hospital_department=form.hospital_department.data,
        patient_treatment_description=form.description.data,
        patient_diagnosis=form.diagnosis.data,
        patient_first_appt_date=form.first_appt_date.data,
        patient_check_in=form.check_in_date.data,
        patient_check_out=form.check_out_date.data,
        patient_treating_doctor=form.treating_doctor.data,
        patient_doctors_phone=form.doctor_phone_number.data,
        patient_social_worker=form.hospital_social_worker.data,
        patient_social_worker_phone=form.sw_phone_number.data,
        inpatient=form.in_or_out_patient.data,
        inpatient_prior=form.staying_prior_to_admission.data,
        vaccinated=form.vaccinated.data,
        comments=form.comments.data,
        wheelchair_access=form.wheelchair_access.data,
        full_bathroom=form.full_bathroom.data,
        pack_n_play=form.pack_n_play.data)

    guests = []
    for i in range(1, 6):
        guest_name = form[f'guest{i}_name'].data
        guest_dob = form[f'guest{i}_dob'].data
        guest_rel = form[f'guest{i}_rel_to_patient'].data
        guest_email = form[f'guest{i}_email'].data
        guest_guardian = form[f'guest{i}_guardian'].data
        if guest_name and guest_dob and guest_rel and guest_email and guest_guardian:
            guests.append(Guest(
                name=guest_name,
                dob=guest_dob,
                relationship_to_patient=guest_rel,
                email=guest_email,
                guardian=guest_guardian))
    room_request.guests = guests

    return room_request

def get_form_from_room_request(room_request):
    """Returns a RoomRequestForm with pre-filled data from the given room request."""
    form = RoomRequestForm(
        first_name=room_request.first_name,
        last_name=room_request.last_name,
        rel_to_patient=room_request.relationship_to_patient,
        street_address=room_request.address_line_one,
        apt_st_address=room_request.address_line_two,
        city=room_request.city,
        state=room_request.state,
        zipcode=room_request.zip_code,
        country=room_request.country,
        phone_number=room_request.primary_phone,
        alt_phone_number=room_request.secondary_phone,
        email=room_request.email,
        primary_language=room_request.primary_language,
        secondary_language=room_request.secondary_language,
        stayed_before=room_request.previous_stay,
        patient_first_name=room_request.patient_first_name,
        patient_last_name=room_request.patient_last_name,
        patient_dob=room_request.patient_dob,
        patient_gender=room_request.patient_gender,
        hospital=room_request.patient_hospital,
        hospital_department=room_request.patient_hospital_department,
        description=room_request.patient_treatment_description,
        diagnosis=room_request.patient_diagnosis,
        first_appt_date=room_request.patient_first_appt_date,
        check_in_date=room_request.patient_check_in,
        check_out_date=room_request.patient_check_out,
        treating_doctor=room_request.patient_treating_doctor,
        doctor_phone_number=room_request.patient_doctors_phone,
        hospital_social_worker=room_request.patient_social_worker,
        sw_phone_number=room_request.patient_social_worker_phone,
        in_or_out_patient=room_request.inpatient,
        staying_prior_to_admission=room_request.inpatient_prior,
        vaccinated=room_request.vaccinated,
        comments=room_request.comments,
        wheelchair_access=room_request.wheelchair_access,
        full_bathroom=room_request.full_bathroom,
        pack_n_play=room_request.pack_n_play)

    for i, guest in enumerate(room_request.guests):
        form[f'guest{i+1}_name'].data = guest.name
        form[f'guest{i+1}_dob'].data = guest.dob
        form[f'guest{i+1}_rel_to_patient'].data = guest.relationship_to_patient
        form[f'guest{i+1}_email'].data = guest.email
        form[f'guest{i+1}_guardian'].data = guest.guardian

    return form
