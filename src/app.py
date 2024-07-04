import os
import tempfile
import zipfile
from flask import Flask, request, render_template, send_file
from document_generator import generate_document

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = {
            '<Applicant>': request.form.get('applicant'),
            '<Age1>': request.form.get('age1'),
            '<Applicants Father>': request.form.get('applicants_father'),
            '<Address1>': request.form.get('address1'),
            '<Co-Applicant>': request.form.get('co_applicant'),
            '<Age2>': request.form.get('age2'),
            '<Co-Applicants Father>': request.form.get('co_applicants_father'),
            '<Co-applicant Address2>': request.form.get('co_applicant_address2'),
            '<Co-Applicant2>': request.form.get('co_applicant2'),
            '<Age3>': request.form.get('age3'),
            '<Co-Applicants Father2>': request.form.get('co_applicants_father2'),
            '<Co-applicants Address3>': request.form.get('co_applicants_address3'),
            '<Co-Applicant3>': request.form.get('co_applicant3'),
            '<Age4>': request.form.get('age4'),
            '<Co-Applicants Father3>': request.form.get('co_applicants_father3'),
            '<Co-applicants Address4>': request.form.get('co_applicants_address4'),
            '<Property Address>': request.form.get('property_address'),
            '<Area>': request.form.get('area'),
            '<Survey Number>': request.form.get('survey_no'),
            '<List1>': request.form.get('list1'),
            '<List2>': request.form.get('list2'),
            '<List3>': request.form.get('list3'),
            '<List4>': request.form.get('list4'),
            '<List5>': request.form.get('list5'),
            '<List6>': request.form.get('list6'),
            '<North>': request.form.get('north'),
            '<South>': request.form.get('south'),
            '<East>': request.form.get('east'),
            '<West>': request.form.get('west'),
            '<Loan Amount>': request.form.get('loan_amount'),
            '<Sanction Date>': request.form.get('sanction_date'),
            '<Take Over From>': request.form.get('take_over_from'),
            '<In words>': request.form.get('in_words'),
            '<Pay Order Amount>': request.form.get('pay_order_amount'),
            '<Payee Name>': request.form.get('payee_name'),
            '<Date>': request.form.get('date'),
        }

        template_name = request.form.get('template_name')
        
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, 'outputs')
        os.makedirs(output_dir, exist_ok=True)

        try:
            # Use the absolute path to ensure correct file reference
            template_path = os.path.join(os.path.abspath('src'), 'templates', template_name)
            print(f"Using template path: {template_path}")
            
            # List files in the templates directory
            templates_dir = os.path.join(os.path.abspath('src'), 'templates')
            available_templates = os.listdir(templates_dir)
            print(f"Available templates: {available_templates}")
            
            if template_name not in available_templates:
                raise FileNotFoundError(f"Template {template_name} not found in {templates_dir}")
            
            document = generate_document(template_path, data)
            output_path = os.path.join(output_dir, template_name)
            document.save(output_path)
            
            output_zip = os.path.join(temp_dir, 'documents.zip')
            with zipfile.ZipFile(output_zip, 'w') as zipf:
                for root, _, files in os.walk(output_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), output_dir))
            
            return send_file(output_zip, as_attachment=True, download_name='documents.zip')
        except Exception as e:
            print(f"Error processing documents: {e}")
            return f"An error occurred while processing the document: {e}. Please try again."

    else:
        templates = os.listdir(os.path.join('src', 'templates'))
        return render_template('index.html', templates=templates)

if __name__ == '__main__':
    app.run(debug=True)
